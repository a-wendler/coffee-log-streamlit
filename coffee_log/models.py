"""Models"""

from __future__ import annotations
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from loguru import logger

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.types import DECIMAL
from pages.mail import send_email

import streamlit as st


class Base(DeclarativeBase):
    pass


class Log(Base):
    """Model für einen Logbucheintrag"""

    __tablename__ = "coffee_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anzahl: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="logs")

    def save(self, session):
        session.add(self)
        session.commit()


class Payment(Base):
    """Model für ein Payment

    Payment typen sind: Einkauf, Rücklage, Korrektur, Auszahlung, Einzahlung, Miete"""

    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    betrag: Mapped[Decimal] = mapped_column(DECIMAL(8, 2), nullable=False)
    betreff: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    typ: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="payments")
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("invoices.id"))
    invoice: Mapped[Optional["Invoice"]] = relationship(back_populates="payments")


class User(Base):
    """Mode für einen User"""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    vorname: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    admin: Mapped[int] = mapped_column(Integer, default=0)
    mitglied: Mapped[int] = mapped_column(Integer, default=0)
    token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, default="new"
    )
    ts: Mapped[datetime] = mapped_column(String(64), nullable=False)
    logs: Mapped[List[Log]] = relationship(back_populates="user")
    payments: Mapped[List[Payment]] = relationship(back_populates="user")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user")


class Invoice(Base):
    """Model für eine Rechnung"""

    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gesamtbetrag: Mapped[Decimal] = mapped_column(DECIMAL(8, 2), nullable=False)
    kaffee_anzahl: Mapped[int] = mapped_column(Integer, nullable=False)
    kaffee_preis: Mapped[Decimal] = mapped_column(DECIMAL(8, 2), nullable=False)
    miete: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(8, 2), nullable=True)
    payment_betrag: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(8, 2), nullable=True
    )
    monat: Mapped[datetime] = mapped_column(String(64), nullable=False)
    email_versand: Mapped[Optional[datetime]] = mapped_column(String(64), nullable=True)
    bezahlt: Mapped[Optional[datetime]] = mapped_column(String(64), nullable=True)
    ts: Mapped[datetime] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="invoices")
    payments: Mapped[List[Payment]] = relationship(back_populates="invoice")

    def mark_as_paid(self, session):
        try:
            # format datum to string of month
            monat = datetime.strptime(self.monat, "%Y-%m-%d %H:%M:%S")
            monat = monat.strftime("%m-%Y")

            self.bezahlt = datetime.now()
            self.payments.append(
                Payment(
                    betrag=self.gesamtbetrag,
                    betreff=f"Rechnung {monat} bezahlt",
                    typ="Einzahlung",
                    ts=datetime.now(),
                    user_id=self.user_id,
                    invoice_id=self.id,
                )
            )
            session.add(self)
            session.commit()
        except Exception as e:
            session.rollback()
            st.error(
                "Die Rechnung konnte nicht als bezahlt markiert werden. Es ist ein Fehler aufgetreten."
            )
            logger.error(f"Rechnung konnte nicht als bezahlt markiert werden: {e}")

    def send_invoice_mail(self, session):
        uebersetzungen = {
            "January": "Januar",
            "February": "Februar",
            "March": "März",
            "April": "April",
            "May": "Mai",
            "June": "Juni",
            "July": "Juli",
            "August": "August",
            "September": "September",
            "October": "Oktober",
            "November": "November",
            "December": "Dezember",
        }
        monat = datetime.strptime(self.monat, "%Y-%m-%d %H:%M:%S")
        monat = uebersetzungen[monat.strftime("%B")] + " " + monat.strftime("%Y")
        subject = f"LSB Kaffeeabrechnung {monat}"
        text = f"""
Ihre Kaffeeabrechnung für {monat}:

Getrunkene Tassen Kaffee: {self.kaffee_anzahl}
Preis für Kaffee: {self.kaffee_preis} €"""
        if self.user.mitglied:
            text += f"""
Mietanteil: {self.miete} €"""
        if self.payment_betrag:
            text += f"""         
Guthaben für Einkäufe etc.: {self.payment_betrag} €
"""
        text += f"""
=========================================================
Gesamtbetrag: {self.gesamtbetrag} €

Bitte überweisen Sie den Betrag an {st.secrets.BANKVERBINDUNG}.
"""
        try:
            send_email(self.user.email, text, subject)
            self.email_versand = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session.commit()
            logger.success(f"Rechnung für {monat} an {self.user.email} versandt.")
            return st.success("Rechnung erfolgreich versandt!")
        except Exception as e:
            session.rollback()
            st.error(
                "Die Rechnung konnte nicht per Email versandt werden. Es ist ein Fehler aufgetreten."
            )
            logger.error(
                f"Rechnung für {monat} an {self.user.email} konnte nicht per Email versandt werden: {e}"
            )
            return e
