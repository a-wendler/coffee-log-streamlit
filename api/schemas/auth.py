"""Auth-related Pydantic schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request body."""

    code: str


class LoginResponse(BaseModel):
    """Login response with JWT and user."""

    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class RegisterRequest(BaseModel):
    """Registration request body."""

    vorname: str
    name: str
    email: str
    code: str
    code_confirm: str


class SetPasswordRequest(BaseModel):
    """Set new password (for reset flow)."""

    token: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    """Request password reset by email."""

    email: str


class UserResponse(BaseModel):
    """User data in API responses."""

    id: int
    name: str
    vorname: str
    email: str
    admin: int
    mitglied: int
    status: str | None

    class Config:
        from_attributes = True
