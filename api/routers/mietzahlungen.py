"""Mietzahlungen router - rent payments."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, extract

from api.auth import get_current_user_id, require_admin
from api.database import get_db_context
from api.models import User, Mietzahlung

router = APIRouter()


class CreateMietzahlungRequest(BaseModel):
    user_id: int
    month: str


def _user_to_dict(user: User) -> dict:
    return {"id": user.id, "admin": user.admin}


@router.get("")
def list_mietzahlungen(
    month: str,
    user_id: int = Depends(get_current_user_id),
):
    """Get rent payments for month (admin). Returns list of users with paid/not paid."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        try:
            year, month_num = map(int, month.split("-"))
            datum = datetime(year, month_num, 1)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
        mietzahlungen = session.scalars(
            select(Mietzahlung).where(
                extract("month", Mietzahlung.monat) == datum.month,
                extract("year", Mietzahlung.monat) == datum.year,
            )
        ).all()
        zahlungsliste = {m.user_id for m in mietzahlungen}
        mitglieder = session.scalars(
            select(User).where(User.mitglied == 1).order_by(User.name)
        ).all()
        return [
            {"user_id": m.id, "name": m.name, "paid": m.id in zahlungsliste}
            for m in mitglieder
        ]


@router.post("")
def create_mietzahlung(
    request: CreateMietzahlungRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Record rent payment (admin for a user, or user for self via users/me/mietzahlung)."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        try:
            year, month_num = map(int, request.month.split("-"))
            datum = datetime(year, month_num, 1)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Month format must be YYYY-MM")
        is_admin = user.admin == 1
        target_user_id = request.user_id if is_admin else user_id
        if not is_admin and request.user_id != user_id:
            raise HTTPException(status_code=403, detail="Kann nur eigene Mietzahlung eintragen")
        existing = session.scalar(
            select(Mietzahlung).where(
                extract("month", Mietzahlung.monat) == datum.month,
                extract("year", Mietzahlung.monat) == datum.year,
                Mietzahlung.user_id == target_user_id,
            )
        )
        if existing:
            raise HTTPException(status_code=400, detail="Mietzahlung bereits eingetragen")
        mz = Mietzahlung(monat=datum, ts=datetime.now(), user_id=target_user_id)
        session.add(mz)
        session.commit()
    return {"message": "Mietzahlung erfolgreich eingetragen!"}
