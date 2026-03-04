"""Compute-heavy business logic: saldo, monatsliste, account overview."""

from decimal import Decimal
from datetime import datetime
from typing import Union, List

from sqlalchemy import select, extract, func, or_
from sqlalchemy.orm import Session, selectinload

from api.models import Log, User, Payment, Invoice, Mietzahlung
from api.config import settings


def quantize_decimal(value: Union[Decimal, int, float, str]) -> Decimal:
    """Round to 2 decimal places."""
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


def get_user_saldo(session: Session, user_id: int) -> Decimal:
    """Compute user saldo: sum(payments) - sum(invoice kaffee_preis)."""
    invoice_sum = session.scalar(
        select(func.sum(Invoice.kaffee_preis)).where(Invoice.user_id == user_id)
    )
    invoice_sum = invoice_sum or Decimal("0")
    payment_sum = session.scalar(
        select(func.sum(Payment.betrag)).where(Payment.user_id == user_id)
    )
    payment_sum = payment_sum or Decimal("0")
    return payment_sum - invoice_sum


def get_anzahl_monatskaffees(session: Session, user_id: int, datum: datetime) -> int:
    """Coffee count for user in given month."""
    result = session.scalar(
        select(func.sum(Log.anzahl)).where(
            extract("month", Log.ts) == datum.month,
            extract("year", Log.ts) == datum.year,
            Log.user_id == user_id,
        )
    )
    return int(result or 0)


def get_account_overview(session: Session) -> dict:
    """Compute full account overview (admin)."""
    users = (
        session.scalars(
            select(User)
            .options(
                selectinload(User.payments),
                selectinload(User.invoices),
                selectinload(User.logs),
            )
            .order_by(User.name)
        )
    ).all()

    preis_mitglied = quantize_decimal(settings.kaffee_preis_mitglied)
    preis_gast = quantize_decimal(settings.kaffee_preis_gast)

    einzahlungen = Decimal("0")
    einkaeufe = Decimal("0")
    auszahlungen = Decimal("0")
    korrekturen = Decimal("0")
    offene_rechnungen = []
    offene_rechnungen_summe = Decimal("0")
    mitgliederkaffees = 0
    gastkaffees = 0
    saldi = []
    summe_positiv = Decimal("0")

    for user in users:
        for payment in user.payments:
            if payment.typ == "Einzahlung":
                einzahlungen += payment.betrag
            elif payment.typ == "Einkauf":
                einkaeufe -= payment.betrag
            elif payment.typ == "Auszahlung":
                auszahlungen += payment.betrag
            elif payment.typ == "Korrektur":
                korrekturen += payment.betrag

        for invoice in user.invoices:
            if invoice.bezahlt is None:
                offene_rechnungen.append(
                    {"Datum": str(invoice.ts), "Betrag": float(invoice.gesamtbetrag), "Nutzer": invoice.user.name}
                )
                offene_rechnungen_summe += invoice.gesamtbetrag

        if user.mitglied:
            mitgliederkaffees += sum(log.anzahl for log in user.logs)
        else:
            gastkaffees += sum(log.anzahl for log in user.logs)

        saldo = get_user_saldo(session, user.id)
        if saldo > 0:
            summe_positiv += saldo
        saldi.append(
            {"Name": user.name, "Vorname": user.vorname, "Mitglied": user.mitglied, "Saldo": float(saldo)}
        )

    mitgliedskosten = mitgliederkaffees * preis_mitglied
    gastkosten = gastkaffees * preis_gast

    return {
        "metrics": {
            "einzahlungen": float(einzahlungen),
            "auszahlungen": float(auszahlungen),
            "korrekturen": float(korrekturen),
            "kassenstand": float(einzahlungen + auszahlungen + korrekturen),
            "offene_rechnungen": float(offene_rechnungen_summe),
            "einkaeufe": float(einkaeufe),
            "mitgliederkaffees": mitgliederkaffees,
            "gastkaffees": gastkaffees,
            "kaffee_gesamt": mitgliederkaffees + gastkaffees,
            "summe_positiv": float(summe_positiv),
            "ueberschuss": float(mitgliedskosten + gastkosten + einkaeufe),
            "mitgliedskosten": float(mitgliedskosten),
            "gastkosten": float(gastkosten),
            "kaffeeumsatz_gesamt": float(mitgliedskosten + gastkosten),
        },
        "offene_rechnungen": offene_rechnungen,
        "saldi": saldi,
    }


def compute_monatsliste(
    session: Session,
    datum: datetime,
    users_with_data: List[User],
) -> List[dict]:
    """Compute invoice preview for month (no DB write)."""
    preis_mitglied = quantize_decimal(settings.kaffee_preis_mitglied)
    preis_gast = quantize_decimal(settings.kaffee_preis_gast)
    invoices = []

    for user in users_with_data:
        kaffee_anzahl = sum(log.anzahl for log in user.logs)
        if kaffee_anzahl == 0:
            continue
        payment_betrag = sum(payment.betrag for payment in user.payments)
        kaffee_preis = (
            kaffee_anzahl * preis_mitglied if user.mitglied else kaffee_anzahl * preis_gast
        )
        saldo = get_user_saldo(session, user.id)
        bezahlt = None
        gesamtbetrag = Decimal("0")

        if saldo > 0:
            if saldo - kaffee_preis < 0:
                gesamtbetrag = kaffee_preis - saldo
            else:
                gesamtbetrag = quantize_decimal("0")
                bezahlt = datetime.now()
        else:
            gesamtbetrag = quantize_decimal(kaffee_preis)

        invoices.append(
            {
                "user_id": user.id,
                "user_name": user.name,
                "kaffee_anzahl": kaffee_anzahl,
                "kaffee_preis": float(kaffee_preis),
                "payment_betrag": float(payment_betrag),
                "gesamtbetrag": float(gesamtbetrag),
                "guthaben_alt": float(saldo),
                "bezahlt": str(bezahlt) if bezahlt else None,
            }
        )
    return invoices


def create_monthly_invoices(session: Session, datum: datetime, users_with_data: List[User]) -> List[Invoice]:
    """Create and persist Invoice records for the month."""
    preis_mitglied = quantize_decimal(settings.kaffee_preis_mitglied)
    preis_gast = quantize_decimal(settings.kaffee_preis_gast)
    created = []

    for user in users_with_data:
        kaffee_anzahl = sum(log.anzahl for log in user.logs)
        if kaffee_anzahl == 0:
            continue
        payment_betrag = sum(payment.betrag for payment in user.payments)
        kaffee_preis = (
            kaffee_anzahl * preis_mitglied if user.mitglied else kaffee_anzahl * preis_gast
        )
        saldo = get_user_saldo(session, user.id)
        bezahlt = None
        gesamtbetrag = Decimal("0")

        if saldo > 0:
            if saldo - kaffee_preis < 0:
                gesamtbetrag = kaffee_preis - saldo
            else:
                gesamtbetrag = quantize_decimal("0")
                bezahlt = datetime.now()
        else:
            gesamtbetrag = quantize_decimal(kaffee_preis)

        monat_str = datum.strftime("%Y-%m-%d %H:%M:%S") if isinstance(datum, datetime) else str(datum)
        invoice = Invoice(
            kaffee_anzahl=kaffee_anzahl,
            kaffee_preis=kaffee_preis,
            payment_betrag=payment_betrag,
            gesamtbetrag=gesamtbetrag,
            monat=monat_str,
            user_id=user.id,
            ts=datetime.now(),
            bezahlt=bezahlt,
        )
        session.add(invoice)
        created.append(invoice)
    session.commit()
    for inv in created:
        session.refresh(inv)
    return created
