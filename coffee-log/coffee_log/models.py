"""Models"""
from __future__ import annotations
from typing import List
from datetime import datetime

from sqlalchemy import Integer, String, Float, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column, Mapped, relationship


class Base(DeclarativeBase):
    pass

class Log(Base):
    """Model für einen Logbucheintrag"""
    __tablename__ = "coffee_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anzahl: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="logs")


class Payment(Base):
    """Model für ein Payment"""
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    betrag: Mapped[float] = mapped_column(Float, nullable=False)
    betreff: Mapped[str] = mapped_column(String)
    ts: Mapped[datetime] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="payments")


class User(Base):
    """Mode für einen User"""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    admin: Mapped[int] = mapped_column(Integer, default=0)
    mitglied: Mapped[int] = mapped_column(Integer, default=0)
    ts: Mapped[datetime] = mapped_column(String, nullable=False)
    logs: Mapped[List[Log]] = relationship(back_populates="user")
    payments: Mapped[List[Payment]] = relationship(back_populates="user")