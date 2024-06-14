from datetime import datetime
import pandas as pd
import streamlit as st
from menu import menu_with_redirect
from pages.monatsuebersicht import get_first_days_of_last_six_months
from models import Log, User, Payment
from sqlalchemy import select, extract, func


def get_subscription_fee():
    # Get the number of members
    with conn.session as session:
        # num_members = session.execute(select(User).where(User.mitglied is True))
        num_members = session.execute(
            func.count(User.id).where(User.mitglied is True)
        ).scalar()
        # session.query(func.count(MyModel.id)).scalar()
        if num_members < 1:
            return 0
        return round(st.secrets.MIETE / num_members, 2)


def gesamt_abrechnung(datum):
    st.header("Gesamtabrechnung")
    with conn.session as session:

        logs = session.execute(
            select(Log).filter(
                extract("month", Log.ts) == datum.month,
                extract("year", Log.ts) == datum.year,
            )
        ).all()
        mitglieder_kaffees = []
        gast_kaffees = []
        for log in logs:
            if log[0].user.mitglied == 1:
                mitglieder_kaffees.append({"Datum": log[0].ts, "Anzahl": log[0].anzahl})
            if log[0].user.mitglied == 0:
                gast_kaffees.append({"Datum": log[0].ts, "Anzahl": log[0].anzahl})
        logs_mitglieder = pd.DataFrame().from_records(mitglieder_kaffees)
        logs_gaeste = pd.DataFrame().from_records(gast_kaffees)

        st.write("Mitgliederkaffees:", logs_mitglieder.Anzahl.sum())
        st.write("Gastkaffees:", logs_gaeste.Anzahl.sum())
        st.write(
            "Gesamtkaffees:", logs_mitglieder.Anzahl.sum() + logs_gaeste.Anzahl.sum()
        )

        payments = session.execute(
            select(Payment).filter(
                extract("month", Payment.ts) == datum.month,
                extract("year", Payment.ts) == datum.year,
            )
        ).all()
        payment_list = []
        for payment in payments:
            payment_list.append(
                {
                    "Datum": payment[0].ts,
                    "Betreff": payment[0].betreff,
                    "Betrag": payment[0].betrag,
                    "Typ": payment[0].typ,
                    "Nutzer": payment[0].user.name,
                }
            )
        payments_df = pd.DataFrame().from_records(payment_list)
        st.subheader("Zahlungen")
        payments_df
        verbrauchskosten = round(payments_df.Betrag.sum(), 2)
        gesamtkosten = round(verbrauchskosten + st.secrets.MIETE, 2)
        gastkaffeekosten = round(logs_gaeste.Anzahl.sum(), 2)
        einzelkaffe_mitglied = (
            gesamtkosten - gastkaffeekosten
        ) / logs_mitglieder.Anzahl.sum()

        einzelposten = []
        einzelposten.append(
            {
                "Betreff": "Verbrauchskosten",
                "Betrag": verbrauchskosten,
            }
        )
        einzelposten.append({"Betreff": "Miete", "Betrag": round(st.secrets.MIETE, 2)})
        einzelposten.append(
            {
                "Betreff": "Gastkaffees",
                "Betrag": -gastkaffeekosten,
            }
        )
        einzelposten_df = pd.DataFrame().from_records(einzelposten)
        st.subheader("Einzelposten")
        st.write(einzelposten_df)
        st.write("Einzelkaffeepreis für Mitglieder:", round(einzelkaffe_mitglied, 2))
        st.write("Gesamtkosten:", gesamtkosten)


def einzelabrechnung(datum):
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
    einzelabrechnung(datum)
