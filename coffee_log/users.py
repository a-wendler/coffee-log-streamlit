"""Module for editing user data."""

import streamlit as st
import pandas as pd
from database.models import User
from sqlalchemy import select


def edit_user_data():
    """Edit user data."""
    with conn.session as session:
        users = session.execute(select(User)).scalars().all()
        df = pd.DataFrame().from_records(
            [
                {
                    "id": user.id,
                    "name": user.name,
                    "vorname": user.vorname,
                    "mitglied": user.mitglied,
                    "admin": user.admin,
                    "email": user.email,
                    "status": user.status,
                }
                for user in users
            ]
        )
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
            for index, row in edited_df.iterrows():
                user = session.query(User).filter(User.id == row["id"]).first()
                user.name = row["name"]
                user.vorname = row["vorname"]
                user.mitglied = row["mitglied"]
                user.admin = row["admin"]
                user.status = row["status"]
                user.email = row["email"]
            session.commit()
            st.success("Änderungen wurden gespeichert!")


# Streamlit app layout
# menu_with_redirect()
conn = st.connection("coffee_counter", type="sql")
st.subheader("Nutzer bearbeiten")
edit_user_data()

