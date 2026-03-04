"""Coffee router - log coffee, get monthly coffee data."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.auth import get_current_user_id
from api.database import get_db_context
from api.models import Log, User

router = APIRouter()


class LogCoffeeRequest(BaseModel):
    anzahl: int


@router.post("")
def log_coffee(
    request: LogCoffeeRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Log coffee consumption. Requires auth."""
    anzahl = request.anzahl
    if anzahl < 1 or anzahl > 5:
        raise HTTPException(status_code=400, detail="Anzahl muss zwischen 1 und 5 liegen")
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        log = Log(
            user_id=user_id,
            anzahl=anzahl,
            ts=datetime.now().isoformat(),
        )
        session.add(log)
        session.commit()
    return {"message": "Ihr Kaffee wurde eingetragen!", "anzahl": anzahl}


@router.get("/month")
def get_coffee_month(
    date: str,
    user_id: int = Depends(get_current_user_id),
):
    """Get coffee list and count for user in given month. Format: YYYY-MM."""
    try:
        year, month = map(int, date.split("-"))
        datum = datetime(year, month, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Date format must be YYYY-MM")
    with get_db_context() as session:
        from sqlalchemy import extract, func

        count = session.scalar(
            select(func.sum(Log.anzahl)).where(
                extract("month", Log.ts) == datum.month,
                extract("year", Log.ts) == datum.year,
                Log.user_id == user_id,
            )
        )
        count = int(count or 0)
        logs = session.scalars(
            select(Log)
            .where(
                extract("month", Log.ts) == datum.month,
                extract("year", Log.ts) == datum.year,
                Log.user_id == user_id,
            )
            .order_by(Log.ts.desc())
        ).all()
        kaffee_liste = [{"id": l.id, "ts": str(l.ts), "anzahl": l.anzahl} for l in logs]
    return {"anzahl": count, "kaffee_liste": kaffee_liste}
