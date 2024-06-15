"""Models"""

from __future__ import annotations
from typing import List, Optional
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
    betreff: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    typ: Mapped[str] = mapped_column(String, nullable=False)
    ts: Mapped[datetime] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="payments")
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"))
    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="payments")


class User(Base):
    """Mode für einen User"""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    vorname: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    admin: Mapped[int] = mapped_column(Integer, default=0)
    mitglied: Mapped[int] = mapped_column(Integer, default=0)
    token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="new")
    ts: Mapped[datetime] = mapped_column(String, nullable=False)
    logs: Mapped[List[Log]] = relationship(back_populates="user")
    payments: Mapped[List[Payment]] = relationship(back_populates="user")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user")


class Invoice(Base):
    """Model für eine Rechnung"""

    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gesamtbetrag: Mapped[float] = mapped_column(Float, nullable=False)
    kaffee_anzahl: Mapped[int] = mapped_column(Integer, nullable=False)
    kaffee_preis: Mapped[float] = mapped_column(Float, nullable=False)
    miete: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payment_betrag: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    monat: Mapped[datetime] = mapped_column(String, nullable=False)
    email_versand: Mapped[Optional[datetime]] = mapped_column(String, nullable=True)
    bezahlt: Mapped[Optional[datetime]] = mapped_column(String, nullable=True)
    ts: Mapped[datetime] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="invoices")
    payments: Mapped[Optional[Payment]] = relationship(back_populates="invoice")
