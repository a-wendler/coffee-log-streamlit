import streamlit as st
import pandas as pd
from sqlalchemy import select
from models import User, Invoice, Payment
from menu import menu_with_redirect


def uebersicht():
    with conn.session as local_session:
        payments_stmt = select(Payment).order_by(Payment.ts.desc())
        payments = local_session.scalars(payments_stmt).all()

        zahlungsliste = []
        for zahlung in payments:
            zahlungsliste.append(
                {
                    "Datum": zahlung.ts,
                    "Betrag": zahlung.betrag,
                    "Typ": zahlung.typ,
                    "Betreff": zahlung.betreff,
                    "Nutzer": zahlung.user.name,
                }
            )

    df = pd.DataFrame(zahlungsliste)
    return st.dataframe(
        df,
        column_config={"Betrag": st.column_config.NumberColumn(format="€ %g")},
    )


# Streamlit app layout
menu_with_redirect()
conn = st.connection("coffee_counter", type="sql")

st.title("Kontoübersicht")
uebersicht()
