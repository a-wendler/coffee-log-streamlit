"""Geschäftslogik für das Ausscheiden von Nutzenden.

Bewusst ohne Streamlit: Diese Funktionen rechnen und buchen, die Seite zeigt
an. Fehler kommen als ``NutzerFehler`` mit einem Text, den die Seite direkt
ausgeben kann.

Warum nicht einfach löschen: Alle Auswertungen joinen von der Tabelle
``users`` nach außen – ``get_user_konten``, ``get_saldi`` und die
Monatsabrechnung starten bei ``select(User)``. Verschwindet die Zeile, fallen
die Kaffees und Zahlungen dieser Person aus *allen* Summen heraus, und
Kaffeeanzahl, Kassenstand und Überschuss ändern sich rückwirkend. Deshalb wird
ein Konto stillgelegt statt gelöscht.

Ebenso wenig wird beim Ausscheiden das Kennzeichen ``mitglied`` angefasst:
``account.py`` teilt die *gesamte* Kaffeehistorie einer Person nach dem
*aktuellen* Kennzeichen in Mitglieder- und Gastkaffees auf. Ein Umschalten
würde jeden je getrunkenen Kaffee nachträglich umpreisen.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from database.models import Invoice, Payment, User
from database.queries import NULL_BETRAG, get_abschluss_daten


class NutzerFehler(Exception):
    """Fachlicher Fehler mit einer Meldung für die Oberfläche."""


# Wie der Restbetrag beim Ausscheiden gebucht wird.
BEZAHLT = "bezahlt"
AUSGEBUCHT = "ausgebucht"


def _hole_user(session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise NutzerFehler("Das Konto existiert nicht mehr.")
    return user


def _andere_aktive_admins(session, user_id: int) -> int:
    """Aktive Admins außer dieser Person."""
    return session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.admin == 1, User.status == "active", User.id != user_id)
    )


def stilllegen(session, user_id: int) -> str:
    """Konto auf "inactive" setzen: kein Login, keine neuen Rechnungen mehr.

    Der Token wird gelöscht, damit ein noch offener Einladungs- oder
    Kennwortlink nicht später doch noch ein Konto aufmacht.

    Zurück kommt der Name als Zeichenkette, nicht das User-Objekt: Nach dem
    Commit sind dessen Attribute abgelaufen und ein Zugriff außerhalb der
    Session läuft in einen DetachedInstanceError.
    """
    user = _hole_user(session, user_id)
    if user.status == "inactive":
        raise NutzerFehler(f"{user.vorname} {user.name} ist bereits stillgelegt.")
    if user.admin == 1 and _andere_aktive_admins(session, user_id) == 0:
        raise NutzerFehler(
            "Das ist der letzte aktive Admin. Machen Sie zuerst jemand anderen "
            "zum Admin, sonst kommt niemand mehr in die Verwaltung."
        )

    name = f"{user.vorname} {user.name}"
    user.status = "inactive"
    user.token = None
    session.commit()
    return name


def reaktivieren(session, user_id: int) -> str:
    """Konto wieder freischalten – das alte Kennwort gilt dann wieder."""
    user = _hole_user(session, user_id)
    if user.status == "active":
        raise NutzerFehler(f"{user.vorname} {user.name} ist bereits aktiv.")

    name = f"{user.vorname} {user.name}"
    user.status = "active"
    session.commit()
    return name


def abschluss_buchen(session, user_id: int, art: str) -> Decimal:
    """Schlussabrechnung: Saldo auf 0 bringen und offene Rechnungen schließen.

    ``art`` sagt, ob echtes Geld geflossen ist:

    * ``BEZAHLT`` – die Person hat beim Gehen bezahlt (Schulden) bzw. ihr
      Guthaben ausgezahlt bekommen. Gebucht wird "Einzahlung" bzw.
      "Auszahlung", das Geld wandert also auch durch den Kassenstand.
    * ``AUSGEBUCHT`` – es fließt kein Geld: Die Gemeinschaft trägt die
      Schulden bzw. behält das Guthaben. Gebucht wird "Abschluss". Diese Art
      zählt in den Saldo, aber nicht in den Kassenstand – sonst stünde Geld in
      der Kasse, das nie angekommen ist.

    Gibt den gebuchten Betrag zurück (positiv = die Kasse bekommt etwas).
    """
    if art not in (BEZAHLT, AUSGEBUCHT):
        raise NutzerFehler(f"Unbekannte Abschlussart: {art}")

    user = _hole_user(session, user_id)
    if user.status != "inactive":
        raise NutzerFehler(
            "Die Schlussabrechnung gibt es nur für stillgelegte Konten. "
            "Legen Sie das Konto zuerst still."
        )

    # Innerhalb der Transaktion frisch rechnen: Zwischen dem Aufbau der Seite
    # und dem Klick kann eine Zahlung dazugekommen sein.
    daten = get_abschluss_daten(session, user_id)
    if daten is None:
        raise NutzerFehler("Das Konto existiert nicht mehr.")
    if not daten.abschlussfaehig:
        raise NutzerFehler(
            f"{daten.unabgerechnete_kaffees} Kaffee(s) stehen noch in keiner "
            "Rechnung. Erst die Monatsabrechnung machen, dann abschließen."
        )
    if daten.erledigt:
        raise NutzerFehler("Für dieses Konto ist nichts mehr offen.")

    betrag = daten.abschlussbetrag
    if art == AUSGEBUCHT:
        typ = "Abschluss"
        betreff = "Ausscheiden: ausgebucht"
    elif betrag > NULL_BETRAG:
        typ = "Einzahlung"
        betreff = "Ausscheiden: Restbetrag bezahlt"
    else:
        # Auszahlungen stehen im Rest der App als negativer Betrag in der
        # Tabelle; betrag ist hier schon negativ.
        typ = "Auszahlung"
        betreff = "Ausscheiden: Guthaben ausgezahlt"

    jetzt = datetime.now()
    # Nur buchen, wenn wirklich etwas offen ist: Ein Saldo von 0 mit einer
    # offenen Rechnung (etwa durch eine Korrektur) braucht keine Zahlung,
    # sondern nur das Schließen der Rechnung.
    if betrag != NULL_BETRAG:
        session.add(
            Payment(
                betrag=betrag,
                betreff=betreff,
                typ=typ,
                ts=jetzt,
                user_id=user_id,
            )
        )

    # Die offenen Rechnungen sind mit der Zahlung oben abgegolten. Sie
    # bekommen deshalb keine eigene Zahlung – der Saldo enthält die
    # Kaffeekosten bereits, eine zweite Buchung würde ihn erneut verschieben.
    for rechnung in session.scalars(
        select(Invoice).where(
            Invoice.user_id == user_id, Invoice.bezahlt.is_(None)
        )
    ):
        rechnung.bezahlt = jetzt

    session.commit()
    return betrag


def loeschen(session, user_id: int) -> str:
    """Konto endgültig löschen – nur ohne jede Historie.

    Sobald Kaffees, Zahlungen, Rechnungen oder Mietzahlungen daranhängen,
    würde das Löschen die Gesamtsummen verändern. Dann bleibt nur das
    Stilllegen. Gedacht ist das hier für Konten, die versehentlich angelegt
    wurden – etwa mit vertippter E-Mail-Adresse.
    """
    user = _hole_user(session, user_id)
    daten = get_abschluss_daten(session, user_id)
    if daten is not None and daten.hat_historie:
        raise NutzerFehler(
            f"{user.vorname} {user.name} hat bereits Kaffees, Zahlungen oder "
            "Rechnungen. Das Konto kann nur stillgelegt werden, sonst ändern "
            "sich die Gesamtsummen rückwirkend."
        )
    if user.admin == 1 and _andere_aktive_admins(session, user_id) == 0:
        raise NutzerFehler("Das ist der letzte aktive Admin.")

    name = f"{user.vorname} {user.name}"
    session.delete(user)
    session.commit()
    return name
