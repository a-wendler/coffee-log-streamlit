import os
from hashlib import sha256
from datetime import datetime

import streamlit as st
from loguru import logger

from models import Log, User
from menu import menu
from login import check_user
from pages.mail import send_reset_email

def reset_password(email):
    """Write reset_key to users-table.
    returns: reset_key to reset the password"""
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
            session.rollback()
            return None
    return token


# Function to log a coffee
def log_coffee():
    """Log a coffee entry."""
    if "user" in st.session_state:
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
        del st.session_state.user
    else:
        st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")

st.header("☕ LSB Kaffeeabrechnung")
conn = st.connection("coffee_counter", type="sql")
menu()
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
        "Kaffee eintragen", type="primary", on_click=check_user, args=(conn,)
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
                st.success(
                    f"Ein Link zum Zurücksetzen Ihres Kennworts wurde an {email} gesendet."
                )
            except Exception as e:
                st.error(f"Beim Senden der E-Mail ist ein Fehler aufgetreten: {e}")
        else:
            st.error("Fehler beim Zurücksetzen des Passwortes!")
st.subheader("So funktioniert es:")
app_path = "https://lsbkaffee.streamlit.app"
page_file_path = "pages/register.py"
page = page_file_path.split("/")[1][0:-3]

st.markdown(
    f"""
    1. <a href="{app_path}/{page}" target="_self">Registrieren</a> Sie sich.
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