import streamlit as st
import pandas as pd
from sqlalchemy import select

from database.models import User, Payment


def zahlungsliste(conn):
    with conn.session as session:
        payments_stmt = select(Payment).order_by(Payment.ts.desc())
        payments = session.scalars(payments_stmt).all()

        zahlungsliste = []
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


# Streamlit app layout
conn = st.connection("coffee_counter", type="sql")

st.title("Kontoübersicht")
zahlungen = zahlungsliste(conn)
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
    st.write(
        "Ein positiver Saldo bedeutet, dass die Person Guthaben hat. Negativer Saldo bedeutet, dass Rechnungen offen sind. Kaffees des laufenden Monats für den noch keine Abrechnung gemacht wurde sind im individuellen Saldo nicht enthalten."
    )
