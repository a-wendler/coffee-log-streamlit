"""Module to register new users."""

import os
from hashlib import sha256
from datetime import datetime

import streamlit as st

from models import User
from menu import menu
from pages.mail import send_activation_email


def add_user(code, name, vorname, email):
    """Add a new user to the database."""
    token = "activate_" + sha256(os.urandom(60)).hexdigest()
    # try:
    with conn.session as session:
        user = User(
            code=sha256(code.encode("utf-8")).hexdigest(),
            name=name,
            vorname=vorname,
            email=email,
            ts=datetime.now().isoformat(),
            token=token,
            status="new",
        )
        session.add(user)
        session.commit()
    # except Exception as e:
    # st.error("Nutzerdaten bereits vorhanden. Fehler: {e}")
    try:
        send_activation_email(email, token)
        st.success(
            f"Nutzer {name} erfolgreich hinzugefügt! Eine E-Mail wurde an {email} gesendet. Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den Link in der E-Mail klicken."
        )
    except Exception as e:
        st.error(f"Beim Senden der Aktivierungsmail ist ein Fehler aufgetreten: {e}")


# Streamlit app layout

# Initialize the database
if "current_user" not in st.session_state:
    st.session_state.current_user = {"name": "", "role": None}
menu()
conn = st.connection("coffee_counter", type="sql")

st.subheader("Neuen Nutzer für die Kaffeeabrechnung hinzufügen")
with st.form(key="add_user", clear_on_submit=True):
    vorname = st.text_input("Vorname")
    name = st.text_input("Nachname")
    email = st.text_input("E-Mail")
    code = st.text_input("Kennwort", type="password")
    submit = st.form_submit_button("Registrieren")

if submit:
    add_user(code, name, vorname, email)
