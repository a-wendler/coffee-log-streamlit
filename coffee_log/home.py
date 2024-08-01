import os
from hashlib import sha256
from datetime import datetime

import streamlit as st
from loguru import logger

from database.models import Log, User
from login import login

from seiten.mail import send_reset_email

def reset_password(email, conn):
    """Write reset-token to users-table.
    returns: reset-token or None"""
    token = "reset_" + sha256(os.urandom(60)).hexdigest()
    with conn.session as session:
        try:
            user = (
                session.query(User)
                .filter(User.email == email, User.status == "active")
                .first()
            )
            user.token = token
            session.commit()
        except Exception as e:
            logger.error(f"Fehler beim Passwortreset: {e}")
            session.rollback()
            return None
    return token


# Function to log a coffee
def log_coffee(conn):
    """Log a coffee entry."""
    if "user" in st.session_state:
        logger.info(f"User: {st.session_state.user.name}")
        with conn.session as session:
            try:
                log = Log(
                    user=st.session_state.user,
                    ts=datetime.now().isoformat(),
                    anzahl=st.session_state.anzahl_slider,
                )
                log.save(session)
                st.success("Ihr Kaffee wurde eingetragen!")
                logger.success(
                    f"{log.anzahl} Kaffee(s) eingetragen von {log.user.name}"
                )
            except Exception as e:
                session.rollback()
                st.error(f"Beim Eintragen des Kaffees ist ein Fehler aufgetreten: {e}")
                logger.error(
                    f"Kaffee konnte nicht eingetragen werden {log.user.name}: {e}"
                )
    else:
        st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")

# st.write(st.session_state)
conn = st.connection("coffee_counter", type="sql")

# st.header("☕ LSB Kaffeeabrechnung")

# st.write(f"Datenbank: {st.secrets.connections.coffee_counter.database}")
st.subheader("Kaffee trinken")
with st.form(key="log_coffee", clear_on_submit=True):
    anzahl = st.select_slider(
        "Wieviele Tassen Kaffee wollen Sie eintragen?",
        options=list(range(1, 6)),
        key="anzahl_slider",
    )
    code = st.text_input(
        "Geben Sie Ihr Kennwort ein.", key="code_input", type="password"
    )
    submit = st.form_submit_button(
        "Kaffee eintragen", type="primary", on_click=login, args=(conn,)
    )

if submit:
    logger.info(f"submit ist gedrückt")
    log_coffee(conn)

with st.expander("Kennwort vergessen?"):
    st.subheader("Kennwort zurücksetzen")
    email = st.text_input("Geben Sie Ihre E-Mail-Adresse ein:")
    if st.button("Kennwort zurücksetzen"):
        reset_key = reset_password(email, conn)
        if reset_key:
            try:
                send_reset_email(email, reset_key)
                st.success(
                    f"Ein Link zum Zurücksetzen Ihres Kennworts wurde an {email} gesendet."
                )
            except Exception as e:
                st.error(f"Beim Senden der E-Mail ist ein Fehler aufgetreten: {e}")
        else:
            st.error("Fehler beim Zurücksetzen des Passwortes!")
st.subheader("So funktioniert es:")

st.markdown(
    f"""
    1. Registrieren Sie sich links im Menü.
    2. Tragen Sie jeden Kaffee in dieses Tool ein, den Sie trinken.
    3. Erhalten Sie am Monatsende eine Abrechnung und zahlen Sie Ihren Anteil.
    
    __Warum digital?__ Die Abrechnung macht keinen Aufwand und Sie haben jederzeit einen Überblick über Ihre Kaffeeausgaben.

    Ein Kaffee kostet € 1,– für Gäste und € 0,25 für Mitglieder, die sich an der Monatsmiete beteiligen. Wenn Sie Mitglied werden wollen, registrieren Sie sich hier und wenden Sie sich an {st.secrets.admins['rechnung']}.
""",
    unsafe_allow_html=True,
)
st.expander("Datenschutz").markdown(
    f"Diese App speichert nur die Daten, die Sie eingeben. Die Daten werden ausschließlich zum Aufteilen der Unkosten für die Kaffeemaschine im 3. OG verwendet. Die Daten sind auf einem Server beim deutschen Anbieter Hetzner in Nürnberg gespeichert. Der Zugriff auf die Daten ist nur für die Administratoren der Kaffeekasse möglich. Sie können jederzeit einen vollständigen Einblick in Ihre Daten erhalten und die Löschung Ihrer Daten verlangen. Bitte wenden Sie sich dazu an {st.secrets.admins['technik']}."
)