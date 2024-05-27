"""Models"""

from typing import List, Optional
from datetime import datetime
import reflex as rx
import sqlmodel


class CoffeeLog(rx.Model, table=True):
    """Model für einen Logbucheintrag"""

    user_id: int = sqlmodel.Field(foreign_key="user.id")
    anzahl: int
    ts: datetime
    user: Optional["User"] = sqlmodel.Relationship(back_populates="logs")


class Payment(rx.Model, table=True):
    """Model für ein Payment"""

    user_id: int = sqlmodel.Field(foreign_key="user.id")
    betrag: float
    betreff: str
    ts: datetime
    user: Optional["User"] = sqlmodel.Relationship(back_populates="payments")


class User(rx.Model, table=True):
    """Mode für einen User"""

    name: str
    email: str
    code: str
    admin: int
    mitglied: int
    ts: datetime
    logs: List[CoffeeLog] = sqlmodel.Relationship(back_populates="user")
    payments: List[Payment] = sqlmodel.Relationship(back_populates="user")
