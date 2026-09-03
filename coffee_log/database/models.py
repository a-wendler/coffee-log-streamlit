"""Models"""

from __future__ import annotations
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from loguru import logger

from sqlalchemy import DateTime, Integer, String, ForeignKey, select, func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.types import DECIMAL

import streamlit as st


class Base(DeclarativeBase):
    pass


# Kontostatus. "new" wartet auf die Aktivierung über den Einladungslink,
# "active" darf sich anmelden, "inactive" ist ausgeschieden: kein Login mehr,
# keine neuen Rechnungen - die Zeilen bleiben aber stehen, weil alle Summen
# über die User-Tabelle gejoint werden und sonst rückwirkend kippen.
STATUS_WERTE = ["new", "active", "inactive"]

# Zahlungsarten. "Abschluss" gleicht das Konto einer ausgeschiedenen Person
# aus, ohne dass Geld fließt: Die Art zählt in den Saldo (der summiert alle
# Zahlungen), aber nicht in den Kassenstand (der zählt Einzahlung, Auszahlung
# und Korrektur auf) - sonst stünde Geld in der Kasse, das nie angekommen ist.
PAYMENT_TYPEN = ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung", "Abschluss"]

# Was im Zahlungsformular von Hand buchbar ist. "Abschluss" fehlt bewusst:
# Diese Buchung entsteht nur über die Schlussabrechnung unter "Nutzer
# verwalten", die den Betrag aus dem Saldo ausrechnet.
PAYMENT_TYPEN_MANUELL = ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung"]


class Log(Base):
    """Model für einen Logbucheintrag"""

    __tablename__ = "coffee_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anzahl: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
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
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
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
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    logs: Mapped[List[Log]] = relationship(back_populates="user")
    payments: Mapped[List[Payment]] = relationship(back_populates="user")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="user")
    mietzahlungen: Mapped[List["Mietzahlung"]] = relationship(back_populates="user")

    def get_saldo(self, conn) -> Decimal:
        """Saldo dieser Person.

        Öffnet eine eigene Session. Wer schon eine Session hat, ruft besser
        ``database.queries.get_saldo(session, user_id)`` direkt auf; wer die
        Saldi mehrerer Personen braucht, ``get_saldi(session)``.
        """
        from database.queries import get_saldo

        with conn.session as session:
            return get_saldo(session, self.id)

    def get_invoices(self, conn) -> List[Invoice]:
        with conn.session as session:
            invoices = session.scalars(
                select(Invoice).where(Invoice.user_id == self.id)
            ).all()
            return invoices
        
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
    monat: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Rechnungen werden nicht mehr per E-Mail versandt. Die Spalte bleibt
    # erhalten, weil sie den Versand alter Rechnungen dokumentiert.
    email_versand: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    bezahlt: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="invoices")
    payments: Mapped[List[Payment]] = relationship(back_populates="invoice")

    def mark_as_paid(self, session):
        session.add(self)
        if self.bezahlt:
            st.error("Die Rechnung wurde bereits bezahlt.")
            logger.error(
                f"Rechnung {self.id} wurde bereits bezahlt und wird nicht erneut gebucht."
            )
            return
        
        try:
            monat = self.monat.strftime("%m-%Y")

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
            session.commit()
        except Exception as e:
            session.rollback()
            st.error(
                "Die Rechnung konnte nicht als bezahlt markiert werden. Es ist ein Fehler aufgetreten."
            )
            logger.error(f"Rechnung konnte nicht als bezahlt markiert werden: {e}")


class Mietzahlung(Base):
    """Model für erfasste Mietzahlungen"""
    __tablename__ = "mietzahlungen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monat: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    user: Mapped["User"] = relationship(back_populates="mietzahlungen")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

if __name__ == "__main__":
    pass