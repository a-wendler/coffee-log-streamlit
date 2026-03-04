"""Module for editing user data via API."""

import streamlit as st
import pandas as pd

from api_client import get, patch


def edit_user_data():
    """Edit user data via API."""
    try:
        users = get("/users")
    except Exception as e:
        st.error(f"Nutzer konnten nicht geladen werden: {e}")
        return
    df = pd.DataFrame([
        {
            "id": u["id"],
            "name": u["name"],
            "vorname": u["vorname"],
            "mitglied": bool(u.get("mitglied", 0)),
            "admin": bool(u.get("admin", 0)),
            "email": u["email"],
            "status": u.get("status", ""),
        }
        for u in users
    ])
    edited_df = st.data_editor(
        df,
        column_config={
            "mitglied": st.column_config.CheckboxColumn(
                "Mitglied",
                help="Ist die Person zahlendes Mitglied der Mietergemeinschaft?",
                default=False,
            ),
            "admin": st.column_config.CheckboxColumn(
                "Admin",
                help="Hat die Person Zugriff auf Abrechnung, Nutzerdaten und Einkäufe?",
                default=False,
            ),
        },
        num_rows="dynamic",
        key="data_editor",
        disabled=["id"],
    )
    if st.button("Änderungen speichern"):
        try:
            for idx, row in edited_df.iterrows():
                orig_id = int(df.iloc[idx]["id"])
                patch(
                    f"/users/{orig_id}",
                    json={
                        "name": str(row["name"]),
                        "vorname": str(row["vorname"]),
                        "mitglied": 1 if row["mitglied"] else 0,
                        "admin": 1 if row["admin"] else 0,
                        "email": str(row["email"]),
                        "status": str(row["status"]),
                    },
                )
            st.success("Änderungen wurden gespeichert!")
            st.rerun()
        except Exception as e:
            st.error(str(e))


st.subheader("Nutzer bearbeiten")
edit_user_data()
