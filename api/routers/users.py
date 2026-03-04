"""Users router - user management, me/saldo, me/invoices, me/mietzahlung."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from pydantic import BaseModel

from api.auth import get_current_user_id, require_admin
from api.database import get_db_context
from api.models import User
from api.services.compute import get_user_saldo

router = APIRouter()


def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "vorname": user.vorname,
        "email": user.email,
        "admin": user.admin,
        "mitglied": user.mitglied,
        "status": user.status,
    }


@router.get("/me/saldo")
def get_me_saldo(user_id: int = Depends(get_current_user_id)):
    """Get current user's saldo."""
    with get_db_context() as session:
        saldo = get_user_saldo(session, user_id)
    return {"saldo": float(saldo)}


@router.get("/me/invoices")
def get_me_invoices(user_id: int = Depends(get_current_user_id)):
    """Get current user's invoices."""
    with get_db_context() as session:
        from api.models import Invoice

        invoices = session.scalars(
            select(Invoice).where(Invoice.user_id == user_id).order_by(Invoice.ts.desc())
        ).all()
        return [
            {
                "id": inv.id,
                "monat": str(inv.monat),
                "gesamtbetrag": float(inv.gesamtbetrag),
                "kaffee_preis": float(inv.kaffee_preis),
                "kaffee_anzahl": inv.kaffee_anzahl,
                "payment_betrag": float(inv.payment_betrag) if inv.payment_betrag else None,
                "bezahlt": str(inv.bezahlt) if inv.bezahlt else None,
                "email_versand": str(inv.email_versand) if inv.email_versand else None,
            }
            for inv in invoices
        ]


@router.get("/me/mietzahlung")
def get_me_mietzahlung_status(
    month: str,
    user_id: int = Depends(get_current_user_id),
):
    """Check if user has paid rent for month. Format: YYYY-MM."""
    try:
        year, month_num = map(int, month.split("-"))
        datum = datetime(year, month_num, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
    with get_db_context() as session:
        from api.models import Mietzahlung
        from sqlalchemy import extract

        mz = session.scalar(
            select(Mietzahlung).where(
                extract("month", Mietzahlung.monat) == datum.month,
                extract("year", Mietzahlung.monat) == datum.year,
                Mietzahlung.user_id == user_id,
            )
        )
    return {"paid": mz is not None}


@router.post("/me/mietzahlung")
def post_me_mietzahlung(
    month: str,
    user_id: int = Depends(get_current_user_id),
):
    """Record rent payment for current user. Format: YYYY-MM."""
    try:
        year, month_num = map(int, month.split("-"))
        datum = datetime(year, month_num, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
    with get_db_context() as session:
        from api.models import Mietzahlung
        from sqlalchemy import extract

        existing = session.scalar(
            select(Mietzahlung).where(
                extract("month", Mietzahlung.monat) == datum.month,
                extract("year", Mietzahlung.monat) == datum.year,
                Mietzahlung.user_id == user_id,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="Mietzahlung bereits eingetragen")
        mz = Mietzahlung(monat=datum, ts=datetime.now(), user_id=user_id)
        session.add(mz)
        session.commit()
    return {"message": "Mietzahlung erfolgreich eingetragen!"}


@router.get("")
def list_users(user_id: int = Depends(get_current_user_id)):
    """List all users (admin) or require admin. Returns user dict for payments selection."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        users = session.scalars(select(User).order_by(User.name)).all()
        return [_user_to_dict(u) for u in users]


class UserUpdate(BaseModel):
    name: str | None = None
    vorname: str | None = None
    email: str | None = None
    status: str | None = None
    mitglied: int | None = None
    admin: int | None = None


@router.patch("/{user_id}")
def update_user(
    user_id: int,
    update: UserUpdate,
    current_user_id: int = Depends(get_current_user_id),
):
    """Update user (admin only)."""
    with get_db_context() as session:
        current = session.scalar(select(User).where(User.id == current_user_id))
        if not current:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(current))
        target = session.scalar(select(User).where(User.id == user_id))
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if update.name is not None:
            target.name = update.name
        if update.vorname is not None:
            target.vorname = update.vorname
        if update.email is not None:
            target.email = update.email
        if update.status is not None:
            target.status = update.status
        if update.mitglied is not None:
            target.mitglied = update.mitglied
        if update.admin is not None:
            target.admin = update.admin
        session.add(target)
        session.commit()
    return {"message": "User updated"}
