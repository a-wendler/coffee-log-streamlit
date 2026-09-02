import streamlit as st
from contextlib import contextmanager
from loguru import logger
from sqlalchemy import select, or_
from sqlalchemy.orm import contains_eager, selectinload
from database.models import Log, User, Payment, Invoice
from database.queries import get_saldi
from db import get_connection
from helpers import get_first_days_of_last_six_months, monatsbereich
from decimal import Decimal
from typing import List, Union
from datetime import datetime


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    try:
        with conn.session as session:
            yield session
            # session.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def quantize_decimal(value: Union[Decimal, int, float, str]) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
    return Decimal(value).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


def monatsliste(datum: datetime, saldi: dict) -> List[Invoice]:

    invoices = []
    for user in st.session_state[datum]["users"]:

        kaffee_anzahl = sum(log.anzahl for log in user.logs)
        if kaffee_anzahl == 0:
            continue
        payment_betrag = sum(payment.betrag for payment in user.payments)

        kaffee_preis = (
            kaffee_anzahl * quantize_decimal(st.secrets.KAFFEEPREIS_MITGLIED)
            if user.mitglied
            else kaffee_anzahl * quantize_decimal(st.secrets.KAFFEEPREIS_GAST)
        )
        saldo = saldi.get(user.id, quantize_decimal("0"))
        bezahlt = None
        if saldo > 0:  # Nutzer hat noch Guthaben
            if saldo - kaffee_preis < 0:  # Nutzer hat nicht genug Guthaben
                gesamtbetrag = (
                    kaffee_preis - saldo
                )  # Guthaben wird verrechnet und Restbetrag ist fällig
            if saldo - kaffee_preis >= 0:  # Nutzer hat genug Guthaben
                gesamtbetrag = quantize_decimal("0")  # es ist keine Zahlung fällig
                bezahlt = datetime.now()
        if saldo <= 0:  # Nutzer hat kein Guthaben
            gesamtbetrag = quantize_decimal(kaffee_preis)

        invoices.append(
            Invoice(
                kaffee_anzahl=kaffee_anzahl,
                kaffee_preis=kaffee_preis,
                payment_betrag=payment_betrag,
                gesamtbetrag=gesamtbetrag,
                monat=datum,
                payments=user.payments,
                user_id=user.id,
                user=user,
                ts=datetime.now(),
                bezahlt=bezahlt,
            )
        )
    st.session_state[datum]["invoices"] = invoices


@st.dialog("Monatsabrechnung erstellen?")
def confirm_monatsabrechnung():
    st.write(
        "Wollen Sie die Monatsabrechnung wirklich erstellen und die Rechnungen einbuchen?"
    )
    if st.button("Ja"):
        monatsbuchung(datum)
        st.rerun()
    if st.button("Nein"):
        st.rerun()


def monatsbuchung(datum):
    with get_db_connection() as session:
        try:
            for invoice in st.session_state[datum]["invoices"]:
                invoice.monat = datum
                invoice.ts = datetime.now()
                session.add(invoice)
            session.commit()
            st.success("Buchung erfolgreich")
        except Exception as e:
            st.error("Fehler bei der Buchung")
            logger.error(f"Fehler bei der Buchung: {e}")
            session.rollback()


# Main Application

conn = get_connection()

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
monate = get_first_days_of_last_six_months()
datum = st.selectbox(
    "Abrechnungsmonat",
    monate,
    format_func=lambda x: uebersetzungen[x.strftime("%B")] + " " + x.strftime("%Y"),
)

if datum:
    if datum not in st.session_state:
        st.session_state[datum] = {}
    monatsstart, monatsende = monatsbereich(datum)
    with get_db_connection() as session:
        # user und payments werden unten für jede Rechnung gebraucht und deshalb
        # gleich mitgeladen – sonst löst jede Rechnung zwei Nachladequeries aus.
        invoices = session.scalars(
            select(Invoice)
            .join(Invoice.user)
            .options(
                contains_eager(Invoice.user),
                selectinload(Invoice.payments),
            )
            .where(Invoice.monat >= monatsstart, Invoice.monat < monatsende)
            .order_by(User.name)
        ).all()

        # wenn für den gewählten Monat noch keine Rechnungen gebucht wurden
        if len(invoices) < 1:
            st.write("Es wurden noch keine Rechnungen für diesen Monat gebucht.")
            if "users" not in st.session_state[datum]:
                st.session_state[datum]["users"] = (
                    session.scalars(
                        select(User)
                        .options(
                            selectinload(
                                User.payments.and_(
                                    Payment.ts >= monatsstart,
                                    Payment.ts < monatsende,
                                    or_(
                                        Payment.typ == "Einkauf",
                                        Payment.typ == "Korrektur",
                                        Payment.typ == "Auszahlung",
                                    ),
                                )
                            ),
                            selectinload(
                                User.logs.and_(
                                    Log.ts >= monatsstart, Log.ts < monatsende
                                )
                            ),
                        )
                        .order_by(User.name)
                    )
                ).all()

            # Alle Saldi in einer Query, statt zweimal pro Person einzeln.
            # no_autoflush, weil weiter unten noch nicht gebuchte Invoice-Objekte
            # an die User gehängt werden: ein Autoflush würde diese Rechnungen
            # vorzeitig in die Datenbank schreiben.
            with session.no_autoflush:
                saldi = get_saldi(session)

            # Gesamtabrechnung
            st.subheader("Gesamtabrechnung")
            mitgliederkaffees = 0
            gastkaffees = 0
            zahlungssumme = quantize_decimal("0")
            for user in st.session_state[datum]["users"]:
                session.add(user)
                mitgliederkaffees += sum(
                    log.anzahl for log in user.logs if user.mitglied
                )
                gastkaffees += sum(log.anzahl for log in user.logs if not user.mitglied)
                zahlungssumme += sum(
                    payment.betrag
                    for payment in user.payments
                    if payment.typ in ["Einkauf", "Korrektur"]
                )

            monatseinnahmen = mitgliederkaffees * quantize_decimal(
                st.secrets.KAFFEEPREIS_MITGLIED
            ) + gastkaffees * quantize_decimal(st.secrets.KAFFEEPREIS_GAST)
            ueberschuss = monatseinnahmen - zahlungssumme

            st.write("Mitgliederkaffees:", mitgliederkaffees)
            st.write("Gastkaffees:", gastkaffees)
            st.write("Gesamtkaffees:", mitgliederkaffees + gastkaffees)
            st.write("Monatseinnahmen: € ", monatseinnahmen)
            st.write("Verbrauchskosten: € ", zahlungssumme)
            st.write("Überschuss: € ", ueberschuss)

            # Zahlungen
            st.subheader("Zahlungen")

            payment_list = []

            for user in st.session_state[datum]["users"]:
                payment_list.extend(
                    [
                        {
                            "Datum": payment.ts,
                            "Betreff": payment.betreff,
                            "Betrag": payment.betrag,
                            "Typ": payment.typ,
                            "Nutzer": user.name,
                        }
                        for payment in user.payments
                        if payment.typ in ["Einkauf", "Korrektur", "Auszahlung"]
                    ]
                )

            st.dataframe(
                payment_list,
                column_config={
                    "Betrag": st.column_config.NumberColumn(format="€ %.2f"),
                    "Datum": st.column_config.DatetimeColumn(format="DD.MM.YYYY"),
                },
            )
            st.subheader("Einzelabrechnungen")
            with st.spinner("Einzelabrechnungen werden erstellt …"):
                if "invoices" not in st.session_state[datum]:
                    monatsliste(datum, saldi)
                show_liste = []

                table = st.dataframe(
                    [
                        {
                            "Name": abrechnung.user.name,
                            "Zahlbetrag": quantize_decimal(abrechnung.gesamtbetrag),
                            "Kaffeeanzahl": abrechnung.kaffee_anzahl,
                            "Kaffeekosten": abrechnung.kaffee_preis,
                            "Einkäufe": abrechnung.payment_betrag,
                            "Guthaben alt": saldi.get(
                                abrechnung.user_id, quantize_decimal("0")
                            ),
                        }
                        for abrechnung in st.session_state[datum]["invoices"]
                    ],
                    column_config={
                        "Zahlbetrag": st.column_config.NumberColumn(format="€ %g"),
                        "Kaffeekosten": st.column_config.NumberColumn(format="€ %g"),
                        "Einkäufe": st.column_config.NumberColumn(format="€ %g"),
                        "Guthaben alt": st.column_config.NumberColumn(format="€ %g"),
                    },
                )
                monatsabrechnung = st.button(
                    f"Monatsabrechnung {uebersetzungen[datum.strftime("%B")]} erstellen"
                )
                if monatsabrechnung:
                    confirm_monatsabrechnung()
        # wenn für den gewählten Monat bereits Rechnungen gebucht wurden
        elif len(invoices) > 0:
            for abrechnung in invoices:
                if abrechnung.bezahlt:
                    bezahlt_icon = "✅"
                else:
                    bezahlt_icon = "❌"
                with st.expander(label=f"{bezahlt_icon} {abrechnung.user.name}"):
                    st.write("Zahlbetrag:", abrechnung.gesamtbetrag)
                    st.write("Kaffeeanzahl:", abrechnung.kaffee_anzahl)
                    st.write("Kaffeekosten:", abrechnung.kaffee_preis)
                    st.write("Einkäufe, Auszahlungen etc.:", abrechnung.payment_betrag)
                    st.write("Erstellt:", abrechnung.ts)
                    st.write("Bezahlt:", abrechnung.bezahlt)
                    st.write("Zahlungen:")
                    for payment in abrechnung.payments:
                        st.write(payment.betrag, payment.betreff, payment.ts)

                    if not abrechnung.bezahlt:
                        st.button(
                            "Rechnung als bezahlt markieren",
                            key=f"paid_{abrechnung.id}",
                            on_click=abrechnung.mark_as_paid,
                            args=(session,),
                        )
                    if abrechnung.gesamtbetrag <= 0:
                        st.write(
                            "Keine Zahlung fällig. Kaffeekosten wurden mit Guthaben verrechnet."
                        )
