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
        for zahlung in payments:
            if zahlung.typ in ["Einkauf"]:
                zahlungsliste.append(
                    {
                        "Datum": zahlung.ts,
                        "Betrag": -zahlung.betrag,
                        "Typ": zahlung.typ,
                        "Betreff": zahlung.betreff,
                        "Nutzer": zahlung.user.name,
                    }
                )
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
        return zahlungsliste


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
zahlungen = zahlungsliste(conn)
df_zahlungen = pd.DataFrame(zahlungen)

einzahlungen = df_zahlungen[df_zahlungen["Typ"] == "Einzahlung"].sum()["Betrag"]
einkaeufe = df_zahlungen[df_zahlungen["Typ"] == "Einkauf"].sum()["Betrag"]
auszahlungen = df_zahlungen[df_zahlungen["Typ"] == "Auszahlung"].sum()["Betrag"]
korrekturen = df_zahlungen[df_zahlungen["Typ"] == "Korrektur"].sum()["Betrag"]

with conn.session as session:
    kaffeeanzahl_mitglieder = session.scalar(
        select(func.sum(Log.anzahl)).join(User).where(User.mitglied == 1)
    )
    kaffeeanzahl_gaeste = session.scalar(
        select(func.sum(Log.anzahl)).join(User).where(User.mitglied == 0)
    )
    mitgliedskosten = kaffeeanzahl_mitglieder * Decimal(st.secrets.KAFFEEPREIS_MITGLIED)
    gastkosten = kaffeeanzahl_gaeste * Decimal(st.secrets.KAFFEEPREIS_GAST)

offene_rechnungen, summe = offene_rechnungen(conn)

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
summe_positiv = df_saldi[df_saldi["Saldo"] > 0]["Saldo"].sum()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Einzahlungen", "€ " + str(einzahlungen).replace(".", ","))
    st.metric("Auszahlungen", "€ " + str(auszahlungen).replace(".", ","))
    st.metric("Korrekturen", "€ " + str(korrekturen).replace(".", ","))
    st.metric(
        "Kassenstand",
        "€ " + str(einzahlungen + auszahlungen + korrekturen).replace(".", ","),
    )
    st.metric("offene Rechnungen", "€ " + str(summe).replace(".", ","))

    st.metric("Einkäufe", "€ " + str(einkaeufe).replace(".", ","))

with col2:

    st.metric("Kaffeeanzahl Mitglieder", str(kaffeeanzahl_mitglieder))
    st.metric("Kaffeeanzahl Gäste", str(kaffeeanzahl_gaeste))
    st.metric("Kaffeeanzahl gesamt", str(kaffeeanzahl_mitglieder + kaffeeanzahl_gaeste))
    st.metric("Summe der Guthaben", "€ " + str(summe_positiv).replace(".", ","))
    st.metric(
        "Überschuss",
        "€ " + str(mitgliedskosten + gastkosten + einkaeufe).replace(".", ","),
    )

with col3:
    st.metric("Kaffeeumsatz Mitglieder", "€ " + str(mitgliedskosten).replace(".", ","))
    st.metric("Kaffeeumsatz Gäste", "€ " + str(gastkosten).replace(".", ","))
    st.metric(
        "Kaffeeumsatz gesamt",
        "€ " + str(mitgliedskosten + gastkosten).replace(".", ","),
    )

# st.dataframe(
#     df_zahlungen,
#     column_config={
#         "Betrag": st.column_config.NumberColumn(format="€ %g"),
#         "Datum": st.column_config.DatetimeColumn(format="DD.MM.YY"),
#     },
# )

st.subheader("offene Rechnungen")

st.dataframe(
    offene_rechnungen,
    column_config={
        "Betrag": st.column_config.NumberColumn(format="€ %g"),
        "Datum": st.column_config.DatetimeColumn(format="DD.MM.YY"),
    },
)


st.subheader("Saldi der Nutzenden")

st.dataframe(
    df_saldi,
    column_config={"Saldo": st.column_config.NumberColumn(format="€ %g")},
)

st.write(
    "Ein positiver Saldo bedeutet, dass die Person Guthaben hat. Negativer Saldo bedeutet, dass Rechnungen offen sind. Kaffees des laufenden Monats für den noch keine Abrechnung gemacht wurde sind im individuellen Saldo nicht enthalten."
)
