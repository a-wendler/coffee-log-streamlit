"""Aggregierte Auswertungs-Queries.

Diese Funktionen fassen Kennzahlen direkt in der Datenbank zusammen, statt
alle Zeilen zu laden und in Python zu summieren. Jede Funktion bekommt eine
bereits geöffnete Session übergeben – so kommt eine Seite mit einer einzigen
Datenbankverbindung aus, statt pro Aufruf eine neue zu öffnen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import case, func, select

from database.models import Invoice, Log, Mietzahlung, Payment, User
from helpers import monatsbereich

NULL_BETRAG = Decimal("0.00")


@dataclass(frozen=True)
class UserKonto:
    """Alle Kennzahlen einer Person – aus einer einzigen Query."""

    id: int
    name: str
    vorname: str
    mitglied: bool
    status: Optional[str]
    einzahlungen: Decimal
    einkaeufe: Decimal
    auszahlungen: Decimal
    korrekturen: Decimal
    abschluesse: Decimal
    zahlungen_summe: Decimal
    rechnungen_summe: Decimal
    kaffees: int

    @property
    def saldo(self) -> Decimal:
        """Guthaben (positiv) bzw. offener Betrag (negativ)."""
        return self.zahlungen_summe - self.rechnungen_summe

    @property
    def aktiv(self) -> bool:
        """Konto ist freigeschaltet (nicht 'new' oder deaktiviert)."""
        return self.status == "active"


def _summe(spalte) -> "func.coalesce":
    """SUM() mit 0 statt NULL, damit in Python nicht geprüft werden muss."""
    return func.coalesce(func.sum(spalte), NULL_BETRAG)


def _betrag_je_typ(typ: str):
    """Teilsumme der Zahlungen eines bestimmten Typs."""
    return _summe(case((Payment.typ == typ, Payment.betrag), else_=NULL_BETRAG))


def _zahlungen_summe_je_user():
    """Subquery: Summe aller Zahlungen je Person."""
    return (
        select(
            Payment.user_id.label("user_id"),
            _summe(Payment.betrag).label("summe"),
        )
        .group_by(Payment.user_id)
        .subquery()
    )


def _rechnungen_summe_je_user():
    """Subquery: Summe aller berechneten Kaffeekosten je Person."""
    return (
        select(
            Invoice.user_id.label("user_id"),
            _summe(Invoice.kaffee_preis).label("summe"),
        )
        .group_by(Invoice.user_id)
        .subquery()
    )


def get_saldi(session) -> Dict[int, Decimal]:
    """Saldo aller Nutzenden als ``{user_id: saldo}`` – eine einzige Query.

    Ersetzt ``User.get_saldo()``, das pro Aufruf eine eigene Session öffnet und
    zwei Queries absetzt. Personen ohne Zahlungen/Rechnungen haben Saldo 0.
    """
    zahlungen = _zahlungen_summe_je_user()
    rechnungen = _rechnungen_summe_je_user()

    stmt = (
        select(
            User.id,
            func.coalesce(zahlungen.c.summe, NULL_BETRAG)
            - func.coalesce(rechnungen.c.summe, NULL_BETRAG),
        )
        .outerjoin(zahlungen, zahlungen.c.user_id == User.id)
        .outerjoin(rechnungen, rechnungen.c.user_id == User.id)
    )
    return {user_id: saldo for user_id, saldo in session.execute(stmt)}


def get_user_konten(session) -> List[UserKonto]:
    """Kennzahlen aller Nutzenden, nach Nachname sortiert.

    Ersetzt das frühere Laden aller Logs/Payments/Invoices plus einem
    ``get_saldo()`` pro Person (2 Queries je Person) durch eine einzige Query.
    """
    zahlungen = (
        select(
            Payment.user_id.label("user_id"),
            _betrag_je_typ("Einzahlung").label("einzahlungen"),
            _betrag_je_typ("Einkauf").label("einkaeufe"),
            _betrag_je_typ("Auszahlung").label("auszahlungen"),
            _betrag_je_typ("Korrektur").label("korrekturen"),
            _betrag_je_typ("Abschluss").label("abschluesse"),
            _summe(Payment.betrag).label("summe"),
        )
        .group_by(Payment.user_id)
        .subquery()
    )

    rechnungen = _rechnungen_summe_je_user()

    kaffees = (
        select(
            Log.user_id.label("user_id"),
            func.coalesce(func.sum(Log.anzahl), 0).label("anzahl"),
        )
        .group_by(Log.user_id)
        .subquery()
    )

    stmt = (
        select(
            User.id,
            User.name,
            User.vorname,
            User.mitglied,
            User.status,
            func.coalesce(zahlungen.c.einzahlungen, NULL_BETRAG),
            func.coalesce(zahlungen.c.einkaeufe, NULL_BETRAG),
            func.coalesce(zahlungen.c.auszahlungen, NULL_BETRAG),
            func.coalesce(zahlungen.c.korrekturen, NULL_BETRAG),
            func.coalesce(zahlungen.c.abschluesse, NULL_BETRAG),
            func.coalesce(zahlungen.c.summe, NULL_BETRAG),
            func.coalesce(rechnungen.c.summe, NULL_BETRAG),
            func.coalesce(kaffees.c.anzahl, 0),
        )
        .outerjoin(zahlungen, zahlungen.c.user_id == User.id)
        .outerjoin(rechnungen, rechnungen.c.user_id == User.id)
        .outerjoin(kaffees, kaffees.c.user_id == User.id)
        .order_by(User.name)
    )

    return [
        UserKonto(
            id=row[0],
            name=row[1],
            vorname=row[2],
            mitglied=bool(row[3]),
            status=row[4],
            einzahlungen=row[5],
            einkaeufe=row[6],
            auszahlungen=row[7],
            korrekturen=row[8],
            abschluesse=row[9],
            zahlungen_summe=row[10],
            rechnungen_summe=row[11],
            kaffees=int(row[12]),
        )
        for row in session.execute(stmt)
    ]


def get_offene_rechnungen(session) -> List[dict]:
    """Alle noch nicht bezahlten Rechnungen inklusive Nutzername."""
    stmt = (
        select(Invoice.ts, Invoice.gesamtbetrag, User.name)
        .join(User, User.id == Invoice.user_id)
        .where(Invoice.bezahlt.is_(None))
        .order_by(Invoice.ts)
    )
    return [
        {"Datum": ts, "Betrag": betrag, "Nutzer": name}
        for ts, betrag, name in session.execute(stmt)
    ]


def get_saldo(session, user_id: int) -> Decimal:
    """Saldo einer einzelnen Person – eine Query statt zwei."""
    zahlungen = (
        select(_summe(Payment.betrag))
        .where(Payment.user_id == user_id)
        .scalar_subquery()
    )
    rechnungen = (
        select(_summe(Invoice.kaffee_preis))
        .where(Invoice.user_id == user_id)
        .scalar_subquery()
    )
    return session.scalar(select(zahlungen - rechnungen))


def get_monatslogs(session, user_id: int, datum: datetime) -> List[Log]:
    """Kaffee-Einträge einer Person in einem Monat, neueste zuerst."""
    start, ende = monatsbereich(datum)
    stmt = (
        select(Log)
        .where(Log.user_id == user_id, Log.ts >= start, Log.ts < ende)
        .order_by(Log.ts.desc())
    )
    return list(session.scalars(stmt))


def get_monatspayments(session, user_id: int, datum: datetime) -> List[Payment]:
    """Zahlungen einer Person in einem Monat."""
    start, ende = monatsbereich(datum)
    stmt = select(Payment).where(
        Payment.user_id == user_id, Payment.ts >= start, Payment.ts < ende
    )
    return list(session.scalars(stmt))


def hat_mietzahlung(session, user_id: int, datum: datetime) -> bool:
    """Ob die Mietzahlung einer Person für den Monat verbucht ist."""
    start, ende = monatsbereich(datum)
    stmt = select(Mietzahlung.id).where(
        Mietzahlung.user_id == user_id,
        Mietzahlung.monat >= start,
        Mietzahlung.monat < ende,
    )
    return session.scalar(stmt) is not None


@dataclass(frozen=True)
class AbschlussDaten:
    """Alles, was für das Ausscheiden einer Person zu entscheiden ist."""

    user_id: int
    name: str
    vorname: str
    status: Optional[str]
    saldo: Decimal
    offene_rechnungen: int
    offener_betrag: Decimal
    unabgerechnete_kaffees: int
    unabgerechnete_monate: List[datetime]
    hat_historie: bool

    @property
    def abschlussbetrag(self) -> Decimal:
        """Betrag, der gebucht werden muss, damit der Saldo auf 0 steht.

        Positiv: Die Person schuldet der Kasse etwas. Negativ: Die Kasse
        schuldet der Person etwas.
        """
        return -self.saldo

    @property
    def abschlussfaehig(self) -> bool:
        """Erst abrechnen, wenn alle Kaffees in einer Rechnung stehen."""
        return self.unabgerechnete_kaffees == 0

    @property
    def erledigt(self) -> bool:
        """Nichts mehr offen: Saldo auf 0 und keine offene Rechnung."""
        return self.saldo == NULL_BETRAG and self.offene_rechnungen == 0


def _anzahl(session, modell, user_id: int) -> int:
    """Zeilen einer Person in einer Tabelle zählen."""
    return session.scalar(
        select(func.count()).select_from(modell).where(modell.user_id == user_id)
    )


def get_abschluss_daten(session, user_id: int) -> Optional[AbschlussDaten]:
    """Stand einer Person für die Schlussabrechnung.

    "Unabgerechnet" sind Kaffees aus Monaten, für die diese Person noch keine
    Rechnung hat - immer auch der laufende Monat. Solange es die gibt, sagt der
    Saldo nicht die Wahrheit über die Schulden, weil die Kaffeekosten erst mit
    der Monatsabrechnung in den Saldo wandern.
    """
    user = session.get(User, user_id)
    if user is None:
        return None

    offene = list(
        session.scalars(
            select(Invoice).where(
                Invoice.user_id == user_id, Invoice.bezahlt.is_(None)
            )
        )
    )

    # Monate, für die schon eine Rechnung existiert - egal ob bezahlt.
    abgerechnet = {
        (monat.year, monat.month)
        for monat in session.scalars(
            select(Invoice.monat).where(Invoice.user_id == user_id)
        )
    }

    offene_kaffees = 0
    offene_monate = {}
    for ts, anzahl in session.execute(
        select(Log.ts, Log.anzahl).where(Log.user_id == user_id)
    ):
        schluessel = (ts.year, ts.month)
        if schluessel not in abgerechnet:
            offene_kaffees += anzahl
            offene_monate.setdefault(schluessel, datetime(ts.year, ts.month, 1))

    anzahl_logs = _anzahl(session, Log, user_id)
    anzahl_payments = _anzahl(session, Payment, user_id)
    anzahl_invoices = _anzahl(session, Invoice, user_id)
    anzahl_mieten = _anzahl(session, Mietzahlung, user_id)

    return AbschlussDaten(
        user_id=user.id,
        name=user.name,
        vorname=user.vorname,
        status=user.status,
        saldo=get_saldo(session, user_id),
        offene_rechnungen=len(offene),
        offener_betrag=sum((r.gesamtbetrag for r in offene), NULL_BETRAG),
        unabgerechnete_kaffees=offene_kaffees,
        unabgerechnete_monate=sorted(offene_monate.values()),
        hat_historie=bool(
            anzahl_logs or anzahl_payments or anzahl_invoices or anzahl_mieten
        ),
    )


def get_rechnungen(session, user_id: int) -> List[Invoice]:
    """Alle Rechnungen einer Person."""
    return list(session.scalars(select(Invoice).where(Invoice.user_id == user_id)))
