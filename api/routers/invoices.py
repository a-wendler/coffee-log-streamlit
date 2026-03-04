"""Invoices router - monthly billing, mark paid, send email."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, extract, or_
from sqlalchemy.orm import selectinload

from api.auth import get_current_user_id, require_admin
from api.database import get_db_context
from api.models import User, Invoice, Payment, Log
from api.services.compute import (
    compute_monatsliste,
    create_monthly_invoices,
    get_user_saldo,
    quantize_decimal,
)
from api.mail import send_invoice_email
from api.config import settings

router = APIRouter()

UEBERSETZUNGEN = {
    "January": "Januar", "February": "Februar", "March": "März", "April": "April",
    "May": "Mai", "June": "Juni", "July": "Juli", "August": "August",
    "September": "September", "October": "Oktober", "November": "November",
    "December": "Dezember",
}


def _user_to_dict(user: User) -> dict:
    return {"id": user.id, "admin": user.admin}


def _format_monat(monat_str: str) -> str:
    """Convert monat string to German month name."""
    try:
        dt = datetime.strptime(monat_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return monat_str
    return UEBERSETZUNGEN.get(dt.strftime("%B"), dt.strftime("%B")) + " " + dt.strftime("%Y")


def _invoice_to_dict(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "user_name": inv.user.name,
        "gesamtbetrag": float(inv.gesamtbetrag),
        "kaffee_anzahl": inv.kaffee_anzahl,
        "kaffee_preis": float(inv.kaffee_preis),
        "payment_betrag": float(inv.payment_betrag) if inv.payment_betrag else None,
        "ts": str(inv.ts),
        "bezahlt": str(inv.bezahlt) if inv.bezahlt else None,
        "email_versand": str(inv.email_versand) if inv.email_versand else None,
        "payments": [
            {"betrag": float(p.betrag), "betreff": p.betreff, "ts": str(p.ts)}
            for p in inv.payments
        ],
    }


@router.get("")
def list_invoices(
    month: str,
    user_id: int = Depends(get_current_user_id),
):
    """Get invoices for month. If none exist, returns computed preview."""
    try:
        year, month_num = map(int, month.split("-"))
        datum = datetime(year, month_num, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        existing = session.scalars(
            select(Invoice)
            .join(User)
            .options(selectinload(Invoice.user), selectinload(Invoice.payments))
            .where(
                extract("month", Invoice.monat) == datum.month,
                extract("year", Invoice.monat) == datum.year,
            )
            .order_by(User.name)
        ).all()
        if existing:
            return {
                "booked": True,
                "invoices": [_invoice_to_dict(inv) for inv in existing],
                "summary": None,
            }
        users_with_data = session.scalars(
            select(User)
            .options(
                selectinload(
                    User.payments.and_(
                        extract("month", Payment.ts) == datum.month,
                        extract("year", Payment.ts) == datum.year,
                        or_(
                            Payment.typ == "Einkauf",
                            Payment.typ == "Korrektur",
                            Payment.typ == "Auszahlung",
                        ),
                    )
                ),
                selectinload(
                    User.logs.and_(
                        extract("month", Log.ts) == datum.month,
                        extract("year", Log.ts) == datum.year,
                    )
                ),
            )
            .order_by(User.name)
        ).all()
        invoice_preview = compute_monatsliste(session, datum, users_with_data)
        mitgliederkaffees = sum(
            sum(log.anzahl for log in u.logs) for u in users_with_data if u.mitglied
        )
        gastkaffees = sum(
            sum(log.anzahl for log in u.logs) for u in users_with_data if not u.mitglied
        )
        zahlungssumme = quantize_decimal("0")
        for u in users_with_data:
            zahlungssumme += sum(
                p.betrag for p in u.payments
                if p.typ in ["Einkauf", "Korrektur"]
            )
        preis_mitglied = quantize_decimal(settings.kaffee_preis_mitglied)
        preis_gast = quantize_decimal(settings.kaffee_preis_gast)
        monatseinnahmen = mitgliederkaffees * preis_mitglied + gastkaffees * preis_gast
        ueberschuss = monatseinnahmen - zahlungssumme
        payment_list = []
        for u in users_with_data:
            payment_list.extend(
                [
                    {
                        "Datum": str(p.ts),
                        "Betreff": p.betreff,
                        "Betrag": float(p.betrag),
                        "Typ": p.typ,
                        "Nutzer": u.name,
                    }
                    for p in u.payments
                    if p.typ in ["Einkauf", "Korrektur", "Auszahlung"]
                ]
            )
        return {
            "booked": False,
            "invoices": invoice_preview,
            "summary": {
                "mitgliederkaffees": mitgliederkaffees,
                "gastkaffees": gastkaffees,
                "monatseinnahmen": float(monatseinnahmen),
                "zahlungssumme": float(zahlungssumme),
                "ueberschuss": float(ueberschuss),
                "payment_list": payment_list,
            },
        }


@router.post("/month")
def create_month_invoices(
    month: str,
    user_id: int = Depends(get_current_user_id),
):
    """Create and persist monthly invoices (admin only)."""
    try:
        year, month_num = map(int, month.split("-"))
        datum = datetime(year, month_num, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        existing = session.scalar(
            select(Invoice).where(
                extract("month", Invoice.monat) == datum.month,
                extract("year", Invoice.monat) == datum.year,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="Rechnungen für diesen Monat bereits gebucht")
        users_with_data = session.scalars(
            select(User)
            .options(
                selectinload(
                    User.payments.and_(
                        extract("month", Payment.ts) == datum.month,
                        extract("year", Payment.ts) == datum.year,
                        or_(
                            Payment.typ == "Einkauf",
                            Payment.typ == "Korrektur",
                            Payment.typ == "Auszahlung",
                        ),
                    )
                ),
                selectinload(
                    User.logs.and_(
                        extract("month", Log.ts) == datum.month,
                        extract("year", Log.ts) == datum.year,
                    )
                ),
            )
            .order_by(User.name)
        ).all()
        created = create_monthly_invoices(session, datum, users_with_data)
    return {"message": "Buchung erfolgreich", "count": len(created)}


@router.post("/{invoice_id}/mark-paid")
def mark_invoice_paid(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Mark invoice as paid (admin only). Creates Einzahlung payment."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        invoice = session.scalar(
            select(Invoice).options(selectinload(Invoice.user)).where(Invoice.id == invoice_id)
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if invoice.bezahlt:
            raise HTTPException(status_code=400, detail="Die Rechnung wurde bereits bezahlt")
        try:
            monat = datetime.strptime(str(invoice.monat), "%Y-%m-%d %H:%M:%S")
            monat_str = monat.strftime("%m-%Y")
        except (ValueError, TypeError):
            monat_str = str(invoice.monat)
        invoice.bezahlt = datetime.now()
        payment = Payment(
            betrag=invoice.gesamtbetrag,
            betreff=f"Rechnung {monat_str} bezahlt",
            typ="Einzahlung",
            ts=str(datetime.now()),
            user_id=invoice.user_id,
            invoice_id=invoice.id,
        )
        session.add(invoice)
        session.add(payment)
        session.commit()
    return {"message": "Rechnung als bezahlt markiert"}


@router.post("/{invoice_id}/send-email")
def send_invoice_email_endpoint(
    invoice_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Send invoice email (admin only)."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        invoice = session.scalar(
            select(Invoice).options(selectinload(Invoice.user)).where(Invoice.id == invoice_id)
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        monat_str = _format_monat(str(invoice.monat))
        saldo = get_user_saldo(session, invoice.user_id)
        send_invoice_email(
            receiver_email=invoice.user.email,
            receiver_name=invoice.user.name,
            receiver_vorname=invoice.user.vorname,
            monat_str=monat_str,
            kaffee_anzahl=invoice.kaffee_anzahl,
            kaffee_preis=float(invoice.kaffee_preis),
            payment_betrag=float(invoice.payment_betrag) if invoice.payment_betrag else None,
            gesamtbetrag=float(invoice.gesamtbetrag),
            saldo=float(saldo),
            zahlungsoptionen=settings.zahlungsoptionen,
        )
        invoice.email_versand = datetime.now()
        session.add(invoice)
        session.commit()
    return {"message": "Rechnung erfolgreich versandt!"}
