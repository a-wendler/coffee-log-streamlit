"""Module for editing payment data via API."""

import streamlit as st
import pandas as pd
from datetime import date
import calendar

from api_client import get, post, patch


def new_payment(user_id: int, betreff: str, typ: str, betrag: float, ts):
    """Add new payment via API."""
    post(
        "/payments",
        json={
            "user_id": user_id,
            "betreff": betreff,
            "typ": typ,
            "betrag": betrag,
            "ts": str(ts) if ts else None,
        },
    )
    st.success("Zahlung wurde hinzugefügt!")


def reset_form(keys):
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()


st.subheader("Zahlung hinzufügen")

try:
    users_data = get("/users")
    mitglieder = [u for u in users_data if u.get("mitglied") == 1]
    user_options = {f"{u['vorname']} {u['name']}": u["id"] for u in mitglieder}
except Exception as e:
    st.error(f"Nutzer konnten nicht geladen werden: {e}")
    mitglieder = []
    user_options = {}

with st.form(key="payment_form", clear_on_submit=True):
    user_selection = st.selectbox(
        "Nutzer",
        options=list(user_options.keys()) or [""],
        key="user_selection",
    )
    user_id = user_options.get(user_selection) if user_selection else None
    betreff = st.text_input("Betreff", key="betreff")
    typ = st.selectbox(
        "Typ",
        ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung"],
        key="typ",
    )
    betrag = st.number_input("Betrag", key="betrag")
    ts = st.date_input("Datum", key="ts", format="DD.MM.YYYY")
    submit = st.form_submit_button("Zahlung hinzufügen")

if submit and user_id is not None:
    try:
        new_payment(user_id, betreff, typ, betrag, ts)
        st.rerun()
    except Exception as e:
        st.error(str(e))

st.subheader("Zahlungen bearbeiten")

try:
    payments = get("/payments")
except Exception as e:
    st.error(f"Zahlungen konnten nicht geladen werden: {e}")
    payments = []

if payments:
    df = pd.DataFrame([
        {
            "ID": p["id"],
            "Einzahler": p.get("user_name", ""),
            "Betrag": p["betrag"],
            "Betreff": p.get("betreff", ""),
            "Typ": p["typ"],
            "Datum": p["ts"],
        }
        for p in payments
    ])
    df_filter = df.copy()

    with st.expander("Tabelle filtern"):
        with st.form("data_editor_filter"):
            left, right = st.columns(2)
            today = date.today()
            filter_einzahler = left.multiselect(
                "Einzahler",
                df["Einzahler"].sort_values().unique().tolist(),
                key="f_einzahler",
            )
            filter_typ = right.multiselect(
                "Typ",
                ["Einkauf", "Korrektur", "Auszahlung", "Einzahlung"],
                key="f_typ",
            )
            start_default = today.replace(day=1)
            end_default = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            filter_datum = left.date_input(
                "Datum",
                value=(start_default, end_default),
                format="DD/MM/YYYY",
                key="f_datum",
            )
            submitted = left.form_submit_button("Filtern")
            reset = left.form_submit_button(
                "Reset",
                on_click=reset_form,
                kwargs={"keys": ["f_einzahler", "f_typ", "f_datum"]},
                type="secondary",
            )
            if submitted:
                mask = pd.Series(True, index=df.index)
                if filter_einzahler:
                    mask &= df["Einzahler"].isin(filter_einzahler)
                if filter_typ:
                    mask &= df["Typ"].isin(filter_typ)
                if isinstance(filter_datum, tuple) and len(filter_datum) == 2:
                    start_date, end_date = filter_datum
                    df["Datum_parsed"] = pd.to_datetime(df["Datum"], format="mixed", errors="coerce")
                    mask &= (df["Datum_parsed"].dt.date >= start_date) & (df["Datum_parsed"].dt.date <= end_date)
                df_filter = df.loc[mask]
            if reset:
                df_filter = df.copy()

    edited_df = st.data_editor(
        df_filter,
        key="data_editor",
        disabled=["ID", "Einzahler"],
    )
    if st.button("Änderungen speichern"):
        try:
            for _, row in edited_df.iterrows():
                payment_id = int(row["ID"])
                patch(
                    f"/payments/{payment_id}",
                    json={
                        "betreff": str(row["Betreff"]) if pd.notna(row["Betreff"]) else None,
                        "typ": str(row["Typ"]),
                        "betrag": float(row["Betrag"]),
                        "ts": str(row["Datum"]) if pd.notna(row["Datum"]) else None,
                    },
                )
            st.success("Änderungen wurden gespeichert!")
            st.rerun()
        except Exception as e:
            st.error(str(e))
else:
    st.write("Keine Zahlungen vorhanden.")
