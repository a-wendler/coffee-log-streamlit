import os
from datetime import datetime
from hashlib import sha256

import streamlit as st
import pandas as pd
from sqlalchemy import select

from models import Log, User
from menu import menu

monatsmiete = 215
kaffeepreis_mitglied = 0.25
kaffeepreis_gast = 1.0


def reset_password(email):
    """Write reset_key to users-table.
    returns: reset_key to reset the password"""
    token = "reset_" + sha256(os.urandom(60)).hexdigest()
    try:
        with conn.session as session:
            user = (
                session.query(User)
                .filter(User.email == email, User.status == "active")
                .first()
            )
            user.token = token
            session.commit()
    except:
        return None
    return token


# Function to log a coffee
def log_coffee():
    """Log a coffee entry."""
    if "user" in st.session_state:
        with conn.session as session:
            log = Log(
                user=st.session_state.user,
                ts=datetime.now().isoformat(),
                anzahl=st.session_state.anzahl_slider,
            )
            session.add(log)
            session.commit()
            st.success("Ihr Kaffee wurde eingetragen!")
            del st.session_state.user
    else:
        st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")


def check_user():
    with conn.session as session:
        try:
            user = (
                session.query(User)
                .filter(
                    User.code
                    == sha256(st.session_state.code_input.encode("utf-8")).hexdigest(),
                    User.status == "active",
                )
                .first()
            )
            st.session_state.current_user["name"] = user.name
            st.session_state.current_user["vorname"] = user.vorname
            st.session_state.current_user["id"] = user.id
            if user.admin:
                st.session_state.current_user["role"] = "admin"
            else:
                st.session_state.current_user["role"] = "user"
            st.session_state.user = user
        except:
            pass


# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

if "current_user" not in st.session_state:
    st.session_state.current_user = {"name": "", "role": None}
st.write(st.session_state)


menu()

st.subheader("So funktioniert es:")
st.markdown(
    """Die Kaffeemaschine wird von einer Gruppe von Kolleg/-innen gemietet.

Wer sich an der Miete beteiligt, bezahlt einen __monatlichen Grundbetrag__ von derzeit € xx und pro Tasse Kaffee 25 ct.
            
Wer als Gast mittrinkt, zahlt € 1 pro Kaffee.

"""
)

st.subheader("Kaffee trinken")
with st.form(key="log_coffee", clear_on_submit=True):
    anzahl = st.select_slider(
        "Wieviele Tassen Kaffee wollen Sie eintragen?",
        options=list(range(1, 6)),
        key="anzahl_slider",
    )
    code = st.text_input("Geben Sie Ihr Kennwort ein.", key="code_input")
    submit = st.form_submit_button(
        "Kaffee eintragen", type="primary", on_click=check_user
    )

if submit:
    log_coffee()

with st.expander("Kennwort vergessen?"):
    st.subheader("Kennwort zurücksetzen")
    email = st.text_input("Geben Sie Ihre E-Mail-Adresse ein:")
    if st.button("Kennwort zurücksetzen"):
        reset_key = reset_password(email)
        st.write(
            f"Ein Link zum Zurücksetzen Ihres Kennworts wurde an {email} gesendet."
        )
        st.write(f"Der Link zum Zurücksetzen Ihres Kennworts lautet {reset_key}.")

st.write(st.session_state)
