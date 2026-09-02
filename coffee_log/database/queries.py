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
from typing import Dict, List

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
    einzahlungen: Decimal
    einkaeufe: Decimal
    auszahlungen: Decimal
    korrekturen: Decimal
    zahlungen_summe: Decimal
    rechnungen_summe: Decimal
    kaffees: int

    @property
    def saldo(self) -> Decimal:
        """Guthaben (positiv) bzw. offener Betrag (negativ)."""
        return self.zahlungen_summe - self.rechnungen_summe


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
            func.coalesce(zahlungen.c.einzahlungen, NULL_BETRAG),
            func.coalesce(zahlungen.c.einkaeufe, NULL_BETRAG),
            func.coalesce(zahlungen.c.auszahlungen, NULL_BETRAG),
            func.coalesce(zahlungen.c.korrekturen, NULL_BETRAG),
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
            einzahlungen=row[4],
            einkaeufe=row[5],
            auszahlungen=row[6],
            korrekturen=row[7],
            zahlungen_summe=row[8],
            rechnungen_summe=row[9],
            kaffees=int(row[10]),
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


def get_rechnungen(session, user_id: int) -> List[Invoice]:
    """Alle Rechnungen einer Person."""
    return list(session.scalars(select(Invoice).where(Invoice.user_id == user_id)))
