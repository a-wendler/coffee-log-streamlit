"""Account router - admin account overview (precomputed metrics)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.auth import get_current_user_id, require_admin
from api.database import get_db_context
from api.models import User
from api.services.compute import get_account_overview

router = APIRouter()


def _user_to_dict(user: User) -> dict:
    return {"id": user.id, "admin": user.admin}


@router.get("/overview")
def get_overview(user_id: int = Depends(get_current_user_id)):
    """Get account overview (admin only). Precomputed metrics."""
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        require_admin(_user_to_dict(user))
        return get_account_overview(session)
