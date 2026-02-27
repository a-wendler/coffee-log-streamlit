"""
Module for editing payment data.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import select
from loguru import logger
from datetime import date
import calendar

from database.models import User, Payment

def new_payment():
    """Add new payment."""
    with conn.session as session:
        try:
            payment = Payment(
                user_id=st.session_state.user_selection,
                betreff=st.session_state.betreff,
                typ=st.session_state.typ,
                betrag=st.session_state.betrag,
                ts=st.session_state.ts,
            )
            if payment.typ == "Auszahlung":
                payment.betrag = -payment.betrag

            payment.save(session)
            st.success("Zahlung wurde hinzugefügt!")
        except Exception as e:
            session.rollback()
            logger.error(f"Beim Hinzufügen der Zahlung ist ein Fehler aufgetreten: {e}")
            st.error(f"Beim Hinzufügen der Zahlung ist ein Fehler aufgetreten: {e}")
        


def edit_payment_data():
    with conn.session as session:
        for index, row in st.session_state.data_editor["edited_rows"].items():
            df_index = edited_df.iloc[int(index), 0]
            payment = session.execute(
                select(Payment).where(Payment.id == int(df_index))
            ).scalar_one()
            for k, v in row.items():
                setattr(payment, k, v)
            session.commit()
        st.success("Änderungen wurden gespeichert!")


def sync_data_editor():
    st.session_state.data_editor = edited_df

def reset_form(keys):
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()

# Streamlit app layout
# menu_with_redirect()
# st.write(st.session_state)
conn = st.connection("coffee_counter", type="sql")
st.subheader("Zahlung hinzufügen")
with st.form(key="payment_form", clear_on_submit=True):
    with conn.session as session:
        user = st.selectbox(
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
            key="user_selection",
        )
    betreff = st.text_input("Betreff", key="betreff")
    typ = st.selectbox(
        "Typ",
        ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung"],
        key="typ",
    )
    betrag = st.number_input("Betrag", key="betrag")
    ts = st.date_input("Datum", key="ts", format="DD.MM.YYYY")
    submit = st.form_submit_button("Zahlung hinzufügen", on_click=new_payment)

st.subheader("Zahlungen bearbeiten")
with conn.session as session:
    payments = session.scalars(select(Payment)).all()
    df = pd.DataFrame().from_records(
        [
            {
                "ID": payment.id,
                "Einzahler": payment.user.name,
                "Betrag": payment.betrag,
                "Betreff": payment.betreff,
                "Typ": payment.typ,
                "Datum": payment.ts,
            }
            for payment in payments
        ]
    )

df_filter = df.copy()

with st.expander('Tabelle filtern'):
    with st.form("data_editor_filter"):
        left, right = st.columns(2)
        today = date.today()

        filter_einzahler = left.multiselect(
            "Einzahler",
            df["Einzahler"].sort_values().unique().tolist(),
            key="f_einzahler"
        )

        filter_typ = right.multiselect(
            "Typ",
            ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung"],
            key="f_typ"
        )

        # default to current month range
        start_default = today.replace(day=1)
        end_default = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        filter_datum = left.date_input(
            "Datum",
            value=(start_default, end_default),
            format="DD/MM/YYYY",
            key="f_datum"
        )

        submitted = left.form_submit_button("Filtern")
        reset = left.form_submit_button("Reset", on_click=reset_form, kwargs={"keys": ["f_einzahler","f_typ","f_datum"]}, type='secondary')

        if submitted:
            # Ensure datetime dtype for comparison
            if not pd.api.types.is_datetime64_any_dtype(df["Datum"]):
                df["Datum"] = pd.to_datetime(df["Datum"], format='mixed').dt.date

            mask = pd.Series(True, index=df.index)

            # Only apply if selections exist
            if filter_einzahler:
                mask &= df["Einzahler"].isin(filter_einzahler)

            if filter_typ:
                mask &= df["Typ"].isin(filter_typ)

            # Date range: st.date_input can return a date or a tuple
            if isinstance(filter_datum, tuple) and len(filter_datum) == 2:
                start_date, end_date = filter_datum
                # compare on .dt.date if column is datetime64; otherwise compare dates directly
                if pd.api.types.is_datetime64_any_dtype(df["Datum"]):
                    mask &= (df["Datum"].dt.date >= start_date) & (df["Datum"].dt.date <= end_date)
                else:
                    mask &= (df["Datum"] >= start_date) & (df["Datum"] <= end_date)

            df_filter = df.loc[mask]

        if reset:
            df_filter = df.copy()

with st.form(key="edit_payment_data"):
    edited_df = st.data_editor(
        df_filter,
        key="data_editor",
        disabled=["id", "name"],
    )
    st.form_submit_button("Änderungen speichern", on_click=edit_payment_data)
