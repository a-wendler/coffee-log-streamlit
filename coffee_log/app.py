import os
from datetime import datetime
from hashlib import sha256

import streamlit as st

from models import Log, User
from menu import menu
from pages.mail import send_reset_email

from login import check_user


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


# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

if "current_user" not in st.session_state:
    st.session_state.current_user = {"name": "", "role": None}
st.write(st.session_state)


menu()
st.header("LSB Kaffeeabrechnung")
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
        if reset_key:
            try:
                send_reset_email(email, reset_key)
                st.write(
                    f"Ein Link zum Zurücksetzen Ihres Kennworts wurde an {email} gesendet."
                )
            except Exception as e:
                st.error(f"Beim Senden der E-Mail ist ein Fehler aufgetreten: {e}")
        else:
            st.error("Fehler beim Zurücksetzen des Passwortes!")
st.subheader("So funktioniert es:")
st.markdown(
    f"""
    1. Registrieren Sie sich.
    2. Tragen Sie jeden Kaffee in dieses Tool ein, den Sie trinken.
    3. Erhalten Sie am Monatsende eine Abrechnung und zahlen Sie Ihren Anteil.
    
    __Warum digital?__ Die Abrechnung macht keinen Aufwand und Sie haben jederzet einen Überblick über Ihre Kaffeeausgaben.

    Ein Kaffee kostet € 1,– für Gäste und € 0,25 für Mitgliede, die sich an der Monatsmiete beteiligen. Wenn Sie Mitglied werden wollen, wenden Sie sich an {st.secrets.admins['rechnung']}.
"""
)
# st.write(st.session_state)
