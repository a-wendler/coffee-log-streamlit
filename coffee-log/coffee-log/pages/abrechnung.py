from datetime import datetime
from typing import List
import pandas as pd
import streamlit as st
from menu import menu_with_redirect
from pages.monatsuebersicht import get_first_days_of_last_six_months
from models import Log, User, Payment, Invoice
from sqlalchemy import select, extract, func


def get_subscription_fee() -> float:
    # Get the number of members
    with conn.session as session:
        num_members = (
            session.query(func.count(User.id)).filter(User.mitglied == True).scalar()
        )
    if num_members < 1:
        return 0
    return round(st.secrets.MIETE / num_members, 2)


def gesamt_abrechnung(datum):
    st.header("Gesamtabrechnung")

    st.write("Mitgliederkaffees:", get_member_coffees(datum))
    st.write("Gastkaffees:", get_guest_coffees(datum))
    st.write("Gesamtkaffees:", get_member_coffees(datum) + get_guest_coffees(datum))

    with conn.session as session:
        payments = (
            session.query(Payment)
            .join(User)
            .filter(
                extract("month", Payment.ts) == datum.month,
                extract("year", Payment.ts) == datum.year,
            )
            .all()
        )
        payment_list = []
        for payment in payments:
            payment_list.append(
                {
                    "Datum": payment.ts,
                    "Betreff": payment.betreff,
                    "Betrag": payment.betrag,
                    "Typ": payment.typ,
                    "Nutzer": payment.user.name,
                }
            )
    payments_df = pd.DataFrame().from_records(payment_list)
    st.subheader("Zahlungen")
    payments_df
    st.write("Verbrauchskosten:", get_payment_sum(datum))
    st.write("Miete:", st.secrets.MIETE)
    st.write("Gesamtkosten:", get_payment_sum(datum) + st.secrets.MIETE)
    st.write("Mitgliederkaffeepreis:", get_member_coffee_price(datum))


def get_member_coffees(month):
    with conn.session as session:
        return (
            session.query(func.sum(Log.anzahl))
            .join(Log.user)
            .filter(
                extract("month", Log.ts) == month.month,
                extract("year", Log.ts) == month.year,
                User.mitglied == 1,
            )
            .scalar()
        )


def get_guest_coffees(month):
    with conn.session as session:
        return (
            session.query(func.sum(Log.anzahl))
            .join(Log.user)
            .filter(
                extract("month", Log.ts) == month.month,
                extract("year", Log.ts) == month.year,
                User.mitglied == 0,
            )
            .scalar()
        )


def get_payment_sum(month):
    with conn.session as session:
        betrag = (
            session.query(func.sum(Payment.betrag))
            .filter(
                extract("month", Payment.ts) == month.month,
                extract("year", Payment.ts) == month.year,
            )
            .scalar()
        )
    if betrag > 0:
        return round(betrag, 2)
    return 0


def get_payments(month) -> List[Payment]:
    with conn.session as session:
        return (
            session.query(Payment)
            .filter(
                extract("month", Payment.ts) == month.month,
                extract("year", Payment.ts) == month.year,
            )
            .all()
        )


def get_member_coffee_price(month):
    member_coffees = get_member_coffees(month)
    guest_coffees = get_guest_coffees(month)
    payment_sum = get_payment_sum(month)

    gesamtkosten = st.secrets.MIETE + payment_sum
    return round((gesamtkosten - guest_coffees) / member_coffees, 2)


def einzelabrechnung(monat, user_id) -> Invoice:
    with conn.session as session:
        kaffee_anzahl = (
            session.query(func.sum(Log.anzahl))
            .filter(
                extract("month", Log.ts) == monat.month,
                extract("year", Log.ts) == monat.year,
                Log.user_id == user_id,
            )
            .scalar()
        )

        payments = (
            session.query(Payment)
            .filter(
                extract("month", Payment.ts) == monat.month,
                extract("year", Payment.ts) == monat.year,
                Payment.user_id == user_id,
            )
            .scalar()
        )

        payment_betrag = (
            session.query(func.sum(Payment.betrag))
            .filter(
                extract("month", Payment.ts) == monat.month,
                extract("year", Payment.ts) == monat.year,
                Payment.user_id == user_id,
            )
            .scalar()
        )

        miete = get_subscription_fee()
        kaffee_preis = get_member_coffee_price(monat) * kaffee_anzahl
        gesamtbetrag = kaffee_preis + miete - payment_betrag

    return Invoice(
        kaffee_anzahl=kaffee_anzahl,
        miete=miete,
        kaffee_preis=kaffee_preis,
        payment_betrag=payment_betrag,
        gesamtbetrag=gesamtbetrag,
        monat=datum,
        payments=payments,
        user_id=user_id,
        ts=datetime.now().isoformat(),
    )


def einzelabrechnung_web(datum):
    st.header("Einzelabrechnung")
    with conn.session as session:
        user_choice = st.selectbox(
            "Nutzer",
            [
                user[0].id
                for user in session.execute(
                    select(User).filter(User.mitglied == 1)
                ).all()
            ],
            format_func=lambda x: session.execute(select(User).filter(User.id == x))
            .first()[0]
            .name,
            key="user",
        )
        logs = session.execute(
            select(Log).filter(
                extract("month", Log.ts) == datum.month,
                extract("year", Log.ts) == datum.year,
                Log.user_id == user_choice,
            )
        ).all()
        log_list = []
        for log in logs:
            log_list.append(
                {
                    "Datum": log[0].ts,
                    "Anzahl": log[0].anzahl,
                }
            )
        logs_df = pd.DataFrame().from_records(log_list)
        st.write(logs_df)
    anzahl_kaffees = logs_df.Anzahl.sum()
    miete_anteilig = get_subscription_fee()

    st.write("Anzahl Kaffees:", anzahl_kaffees)
    st.write("Miete anteilig:", miete_anteilig)


menu_with_redirect()

# Streamlit app layout

conn = st.connection("coffee_counter", type="sql")
st.subheader("Abrechnung")

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
monatsliste = get_first_days_of_last_six_months()
datum = st.selectbox(
    "Abrechnungsmonat",
    monatsliste,
    format_func=lambda x: uebersetzungen[x.strftime("%B")] + " " + x.strftime("%Y"),
)
st.write(datum)
if datum:
    gesamt_abrechnung(datum)
    st.subheader("Einzelabrechnung")
    st.write(einzelabrechnung(datum, 1))
