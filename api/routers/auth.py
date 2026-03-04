"""Auth router - login, register, activate, reset-password, set-password."""

import os
import re
from hashlib import sha256
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.auth import hash_password, create_access_token
from api.database import get_db_context
from api.mail import send_activation_email, send_reset_email
from api.models import User
from api.config import settings
from api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    SetPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
)

router = APIRouter()


def _user_to_response(user: User) -> UserResponse:
    """Convert User model to response schema."""
    return UserResponse(
        id=user.id,
        name=user.name,
        vorname=user.vorname,
        email=user.email,
        admin=user.admin,
        mitglied=user.mitglied,
        status=user.status,
    )


def _is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[\+\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Authenticate user and return JWT."""
    if not request.code:
        raise HTTPException(status_code=400, detail="Kennwort erforderlich")
    code_hash = hash_password(request.code)
    with get_db_context() as session:
        user = session.scalar(
            select(User).where(
                User.code == code_hash,
                User.status == "active",
            )
        )
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!",
            )
        token = create_access_token(data={"sub": str(user.id)})
        return LoginResponse(
            access_token=token,
            user=_user_to_response(user),
        )


@router.post("/register")
def register(request: RegisterRequest):
    """Register new user and send activation email."""
    if not all([request.vorname, request.name, request.email, request.code]):
        raise HTTPException(status_code=400, detail="Alle Felder sind Pflichtfelder")
    if not _is_valid_email(request.email):
        raise HTTPException(
            status_code=400,
            detail="Bitte geben Sie eine gültige E-Mail-Adresse ein.",
        )
    if request.code != request.code_confirm:
        raise HTTPException(status_code=400, detail="Die Passworte stimmen nicht überein")
    token = "activate_" + sha256(os.urandom(60)).hexdigest()
    code_hash = hash_password(request.code)
    try:
        with get_db_context() as session:
            user = User(
                code=code_hash,
                name=request.name,
                vorname=request.vorname,
                email=request.email,
                ts=datetime.now().isoformat(),
                token=token,
                status="new",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            send_activation_email(
                request.email,
                token,
                settings.streamlit_app_url,
                settings.admin_technik,
            )
            return {
                "message": f"Nutzer {request.name} erfolgreich hinzugefügt! Eine E-Mail wurde an {request.email} gesendet."
            }
    except Exception as e:
        if "Duplicate" in str(e) or "UNIQUE" in str(e):
            raise HTTPException(
                status_code=400,
                detail="Nutzer konnte nicht registriert werden. Wurde die E-Mailadresse bereits registriert?",
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activate")
def activate(token: str):
    """Activate user account via token from email link."""
    if not token or not token.startswith("activate_"):
        raise HTTPException(status_code=400, detail="Ungültiger Link!")
    with get_db_context() as session:
        user = session.scalar(select(User).where(User.token == token))
        if not user:
            raise HTTPException(status_code=400, detail="Ungültiger Link!")
        user.status = "active"
        user.token = None
        session.add(user)
        session.commit()
    return {"message": "Ihr Konto wurde aktiviert!"}


@router.post("/reset-password")
def request_reset_password(request: ResetPasswordRequest):
    """Request password reset - sends email with reset link."""
    with get_db_context() as session:
        user = session.scalar(
            select(User).where(
                User.email == request.email,
                User.status == "active",
            )
        )
        if not user:
            return {"message": "Falls ein Konto mit dieser E-Mail existiert, wurde ein Link gesendet."}
        reset_token = "reset_" + sha256(os.urandom(60)).hexdigest()
        user.token = reset_token
        session.add(user)
        session.commit()
        send_reset_email(
            request.email,
            reset_token,
            settings.streamlit_app_url,
            settings.admin_rechnung,
            settings.admin_technik,
        )
    return {"message": f"Ein Link zum Zurücksetzen Ihres Kennworts wurde an {request.email} gesendet."}


@router.post("/set-password")
def set_password(request: SetPasswordRequest):
    """Set new password using reset token."""
    if not request.token or not request.token.startswith("reset_"):
        raise HTTPException(status_code=400, detail="Ungültiger Link!")
    if not request.new_password:
        raise HTTPException(status_code=400, detail="Neues Kennwort erforderlich")
    with get_db_context() as session:
        user = session.scalar(
            select(User).where(
                User.token == request.token,
                User.status == "active",
            )
        )
        if not user:
            raise HTTPException(status_code=400, detail="Ungültiger Link!")
        user.code = hash_password(request.new_password)
        user.token = None
        session.add(user)
        session.commit()
    return {"message": "Kennwort wurde geändert!"}
