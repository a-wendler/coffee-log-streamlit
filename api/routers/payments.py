"""Payments router - CRUD for admin, user's payments for my_coffee."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, extract
from pydantic import BaseModel

from api.auth import get_current_user_id, require_admin
from api.database import get_db_context
from api.models import User, Payment

router = APIRouter()


def _user_to_dict(user: User) -> dict:
    return {"id": user.id, "name": user.name, "admin": user.admin}


@router.get("")
def list_payments(
    month: str | None = None,
    user_id: int = Depends(get_current_user_id),
):
    """Get payments. If month (YYYY-MM) provided: current user's payments in that month.
    If no month and admin: all payments."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if month:
            try:
                year, month_num = map(int, month.split("-"))
                datum = datetime(year, month_num, 1)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
            payments = session.scalars(
                select(Payment)
                .where(
                    extract("month", Payment.ts) == datum.month,
                    extract("year", Payment.ts) == datum.year,
                    Payment.user_id == user_id,
                )
                .order_by(Payment.ts.desc())
            ).all()
        else:
            require_admin(_user_to_dict(user))
            payments = session.scalars(
                select(Payment).options(Payment.user).order_by(Payment.ts.desc())
            ).all()
        return [
            {
                "id": p.id,
                "ts": str(p.ts),
                "typ": p.typ,
                "betrag": float(p.betrag),
                "betreff": p.betreff,
                "user_id": p.user_id,
                "user_name": p.user.name if hasattr(p, "user") and p.user else None,
            }
            for p in payments
        ]


class CreatePaymentRequest(BaseModel):
    user_id: int
    betreff: str | None = None
    typ: str
    betrag: float
    ts: str


class UpdatePaymentRequest(BaseModel):
    betreff: str | None = None
    typ: str | None = None
    betrag: float | None = None
    ts: str | None = None


@router.post("")
def create_payment(
    request: CreatePaymentRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Create payment (admin only)."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        if request.typ not in ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung"]:
            raise HTTPException(status_code=400, detail="Ungültiger Zahlungstyp")
        betrag = request.betrag
        if request.typ == "Auszahlung":
            betrag = -betrag
        payment = Payment(
            user_id=request.user_id,
            betreff=request.betreff or "",
            typ=request.typ,
            betrag=betrag,
            ts=request.ts,
        )
        session.add(payment)
        session.commit()
        session.refresh(payment)
    return {"message": "Zahlung wurde hinzugefügt!", "id": payment.id}


@router.patch("/{payment_id}")
def update_payment(
    payment_id: int,
    request: UpdatePaymentRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Update payment (admin only)."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        payment = session.scalar(select(Payment).where(Payment.id == payment_id))
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        if request.betreff is not None:
            payment.betreff = request.betreff
        if request.typ is not None:
            payment.typ = request.typ
        if request.betrag is not None:
            payment.betrag = request.betrag
        if request.ts is not None:
            payment.ts = request.ts
        session.add(payment)
        session.commit()
    return {"message": "Änderungen wurden gespeichert!"}
