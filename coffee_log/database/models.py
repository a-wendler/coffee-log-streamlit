"""Models"""

from __future__ import annotations
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from loguru import logger

from sqlalchemy import Integer, String, ForeignKey, select, extract, func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.types import DECIMAL
from seiten.mail import send_email

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
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern eines Log-Eintrags: {e}")
            session.rollback()


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

    def save(self, session):
        try:
            session.add(self)
            session.commit()
        except Exception as e:
            logger.error(f"Fehler beim Speichern eines Payments: {e}")
            session.rollback()


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
    mietzahlungen: Mapped[List["Mietzahlung"]] = relationship(back_populates="user")

    def get_anzahl_monatskaffees(self, datum: datetime, conn) -> int:
        if not isinstance(datum, datetime):
            raise ValueError("Argument 'datum' muss ein datetime-Objekt sein")
        with conn.session as session:
            coffee_number_stmt = select(func.sum(Log.anzahl)).where(
                extract("month", Log.ts) == datum.month,
                extract("year", Log.ts) == datum.year,
                Log.user_id == self.id,
            )

            kaffeemenge = session.scalar(coffee_number_stmt)
            if kaffeemenge:
                if kaffeemenge > 0:
                    return kaffeemenge
            return 0

    def get_payments(self, datum, conn) -> List[Payment]:
        with conn.session as session:
            payments = session.scalars(
                select(Payment).where(
                    extract("month", Payment.ts) == datum.month,
                    extract("year", Payment.ts) == datum.year,
                    Payment.user_id == self.id,
                )
            ).all()
            return payments

    def get_saldo(self, conn) -> Decimal:

        with conn.session as session:
            invoice_sum = session.scalar(

                select(func.sum(Invoice.kaffee_preis)).where(
                    Invoice.user_id == self.id,
                )
            )
            if not invoice_sum:
                invoice_sum = 0

            payment_sum = session.scalar(
                select(func.sum(Payment.betrag)).where(
                    Payment.user_id == self.id
                )
            )

            if not payment_sum:
                payment_sum = 0
        return payment_sum - invoice_sum

    def get_invoices(self, conn) -> List[Invoice]:
        with conn.session as session:
            invoices = session.scalars(
                select(Invoice).where(Invoice.user_id == self.id)
            ).all()
            return invoices
        
    def kaffee_liste(self, conn, datum):
        if not isinstance(datum, datetime):
            raise ValueError("Argument 'datum' muss ein datetime-Objekt sein")
        with conn.session as session:
            coffee_stmt = (
                select(Log)
                .where(
                    Log.user_id == self.id,
                    extract("month", Log.ts) == datum.month,
                    extract("year", Log.ts) == datum.year,
                )
                .order_by(Log.ts.desc())
            )
            coffee_list = session.scalars(coffee_stmt).all()
            if not coffee_list:
                return None
            return coffee_list
    
    def mietzahlung_eintragen(self, conn, datum):
        with conn.session as session:
            try:
                mietzahlung = Mietzahlung(monat=datum, ts=datetime.now(), user_id=self.id)
                session.add(mietzahlung)
                session.commit()
                logger.success(f"Mietzahlung für {datum} von {self.name} {self.vorname} eingetragen.")
                return st.success("Mietzahlung erfolgreich eingetragen!")
            except Exception as e:
                session.rollback()
                logger.error(f"Mietzahlung für {datum} von {self.name} {self.vorname} konnte nicht eingetragen werden: {e}")
                return st.error("Mietzahlung konnte nicht eingetragen werden.")
    
    def get_mietzahlung_status(self, conn, datum):
        with conn.session as session:
            mietzahlung = session.scalar(select(Mietzahlung).where(
                extract("month", Mietzahlung.monat) == datum.month,
                extract("year", Mietzahlung.monat) == datum.year,
                Mietzahlung.user_id == self.id,
            ))
            if mietzahlung:
                return True
            return False


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

    def mark_as_paid(self, conn):
        if self.bezahlt:
            st.error("Die Rechnung wurde bereits bezahlt.")
            logger.error(
                f"Rechnung {self.id} wurde bereits bezahlt und wird nicht erneut gebucht."
            )
            return
        with conn.session as session:
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

    def send_invoice_mail(self, conn):
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
        Guten Tag {self.user.vorname} {self.user.name},
Ihre Kaffeeabrechnung für {monat}:

Getrunkene Tassen Kaffee: {self.kaffee_anzahl}
Preis für Kaffee: {self.kaffee_preis} €"""
        if self.payment_betrag:
            text += f"""         
Einkäufe diesen Monat: {self.payment_betrag} €
"""
        with conn.session as session:
            if self.gesamtbetrag < self.kaffee_preis:
                if self.gesamtbetrag == 0:
                    text += f"""
Ihr bestehendes Guthaben wurde mit den Kosten für diesen Monat verrechnet.

Sie müssen nichts überweisen.

Ihr aktuelles Guthaben beträgt: {self.user.get_saldo(conn)} €
"""
                if self.gesamtbetrag > 0:
                    text += f"""
Ihr bestehendes Guthaben wurde mit den Kosten für diesen Monat verrechnet.

Sie müssen nur den Restbetrag von {self.gesamtbetrag} € überweisen.

{st.secrets.ZAHLUNGSOPTIONEN}
"""
            if self.gesamtbetrag == self.kaffee_preis:
                text += f"""
=========================================================
Gesamtbetrag: {self.gesamtbetrag} €

{st.secrets.ZAHLUNGSOPTIONEN}
"""
            try:
                send_email(self.user.email, text, subject)
                self.email_versand = datetime.now()
                session.add(self)
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

class Mietzahlung(Base):
    """Model für erfasste Mietzahlungen"""
    __tablename__ = "mietzahlungen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monat: Mapped[datetime] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(String(64), nullable=False)
    user: Mapped["User"] = relationship(back_populates="mietzahlungen")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

if __name__ == "__main__":
    pass