import streamlit as st
import pandas as pd
from sqlalchemy import select, func
from decimal import Decimal

from database.models import User, Payment, Invoice, Log


def zahlungsliste(conn):
    with conn.session as session:
        payments_stmt = select(Payment).order_by(Payment.ts.desc())
        payments = session.scalars(payments_stmt).all()

        zahlungsliste = []
        sollposten = 0
        habenposten = 0
        for zahlung in payments:
            if zahlung.typ in ["Auszahlung", "Einkauf"]:
                zahlungsliste.append(
                    {
                        "Datum": zahlung.ts,
                        "Betrag": -zahlung.betrag,
                        "Typ": zahlung.typ,
                        "Betreff": zahlung.betreff,
                        "Nutzer": zahlung.user.name,
                    }
                )
                sollposten += zahlung.betrag
            else:
                zahlungsliste.append(
                    {
                        "Datum": zahlung.ts,
                        "Betrag": zahlung.betrag,
                        "Typ": zahlung.typ,
                        "Betreff": zahlung.betreff,
                        "Nutzer": zahlung.user.name,
                    }
                )
                habenposten += zahlung.betrag
        return (zahlungsliste, sollposten, habenposten)


@st.cache_data(ttl=180)
def offene_rechnungen(_conn):
    with conn.session as session:
        rechnungen = session.scalars(
            select(Invoice).where(Invoice.bezahlt == None)
        ).all()
        return (
            [
                {
                    "Datum": rechnung.ts,
                    "Betrag": rechnung.gesamtbetrag,
                    "Nutzer": rechnung.user.name,
                }
                for rechnung in rechnungen
            ],
            sum([rechnung.gesamtbetrag for rechnung in rechnungen]),
        )


# Streamlit app layout
conn = st.connection("coffee_counter", type="sql")

st.title("Kontoübersicht")
zahlungen, sollposten, habenposten = zahlungsliste(conn)
df_zahlungen = pd.DataFrame(zahlungen)
st.dataframe(
    df_zahlungen,
    column_config={
        "Betrag": st.column_config.NumberColumn(format="€ %g"),
        "Datum": st.column_config.DatetimeColumn(format="DD.MM.YY"),
    },
)

saldo = "€ " + str(df_zahlungen["Betrag"].sum()).replace(".", ",")
st.metric("Kontostand", saldo)

st.metric("Sollposten", "€ " + str(sollposten).replace(".", ","))
st.metric("Habenposten", "€ " + str(habenposten).replace(".", ","))

with conn.session as session:
    kaffeeanzahl_mitglieder = session.scalar(
        select(func.sum(Log.anzahl)).join(User).where(User.mitglied == 1)
    )
    kaffeeanzahl_gaeste = session.scalar(
        select(func.sum(Log.anzahl)).join(User).where(User.mitglied == 0)
    )
    mitgliedskosten = kaffeeanzahl_mitglieder * Decimal(st.secrets.KAFFEEPREIS_MITGLIED)
    gastkosten = kaffeeanzahl_gaeste * Decimal(st.secrets.KAFFEEPREIS_GAST)

    st.metric("Kaffeeanzahl Mitglieder", str(kaffeeanzahl_mitglieder))
    st.metric("Kaffeeanzahl Gäste", str(kaffeeanzahl_gaeste))
    st.metric("Kaffeeumsatz Mitglieder", "€ " + str(mitgliedskosten).replace(".", ","))
    st.metric("Kaffeeumsatz Gäste", "€ " + str(gastkosten).replace(".", ","))

st.subheader("offene Rechnungen")
offene_rechnungen, summe = offene_rechnungen(conn)
st.dataframe(
    offene_rechnungen,
    column_config={
        "Betrag": st.column_config.NumberColumn(format="€ %g"),
        "Datum": st.column_config.DatetimeColumn(format="DD.MM.YY"),
    },
)
st.metric("Summe offene Rechnungen", "€ " + str(summe).replace(".", ","))

st.subheader("Saldi der Nutzenden")
with conn.session as session:
    users = session.scalars(select(User).where(User.status == "active")).all()
    df_saldi = pd.DataFrame().from_records(
        [
            {
                "Name": user.name,
                "Vorname": user.vorname,
                "Mitglied": user.mitglied,
                "Saldo": user.get_saldo(conn),
            }
            for user in users
        ]
    )
    st.dataframe(
        df_saldi,
        column_config={"Saldo": st.column_config.NumberColumn(format="€ %g")},
    )
    summe = df_saldi["Saldo"].sum()
    # calculate the sum of all positive saldos
    summe_positiv = df_saldi[df_saldi["Saldo"] > 0]["Saldo"].sum()
    st.metric("Summe aller Saldi", "€ " + str(summe).replace(".", ","))
    st.metric("Summe der Guthaben", "€ " + str(summe_positiv).replace(".", ","))
    st.write(
        "Ein positiver Saldo bedeutet, dass die Person Guthaben hat. Negativer Saldo bedeutet, dass Rechnungen offen sind. Kaffees des laufenden Monats für den noch keine Abrechnung gemacht wurde sind im individuellen Saldo nicht enthalten."
    )
