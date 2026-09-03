from datetime import datetime

import streamlit as st
from loguru import logger

from database.models import Log
from login import login

from db import get_connection


# Function to log a coffee
def log_coffee(conn):
    """Trägt den Kaffee ein. Gibt zurück, ob es geklappt hat."""
    if "user" not in st.session_state:
        # Ohne Anmeldung kommt man hier nur nach einem gescheiterten Login
        # durch das Formular - login() hat die Meldung dazu schon ausgegeben.
        return False

    logger.info(f"User: {st.session_state.user.name}")
    anzahl = st.session_state.anzahl_slider
    with conn.session as session:
        try:
            log = Log(
                user=st.session_state.user,
                ts=datetime.now(),
                anzahl=anzahl,
            )
            log.save(session)
            logger.success(f"{anzahl} Kaffee(s) eingetragen von {log.user.name}")
        except Exception as e:
            session.rollback()
            st.error(f"Beim Eintragen des Kaffees ist ein Fehler aufgetreten: {e}")
            logger.error(f"Kaffee konnte nicht eingetragen werden: {e}")
            return False

    # Die Bestätigung zeigt die Kaffeeübersicht an, auf die es gleich
    # weitergeht: Ein st.success hier wäre nach dem Seitenwechsel weg.
    st.session_state["kaffee_gebucht"] = anzahl
    return True

# st.write(st.session_state)
conn = get_connection()

# st.header("☕ LSB Kaffeeabrechnung")

# st.write(f"Datenbank: {st.secrets.connections.coffee_counter.database}")
st.subheader("Kaffee trinken")
with st.form(key="log_coffee", clear_on_submit=True):
    anzahl = st.select_slider(
        "Wieviele Tassen Kaffee wollen Sie eintragen?",
        options=list(range(1, 6)),
        key="anzahl_slider",
    )
    if "user" in st.session_state:
        submit = st.form_submit_button(
            "Kaffee eintragen", type="primary")
    else:
        code = st.text_input(
            "Geben Sie Ihr Kennwort ein.", key="code_input", type="password"
        )
        submit = st.form_submit_button(
            "Kaffee eintragen", type="primary", on_click=login, args=(conn,)
        )

if submit and log_coffee(conn):
    # Direkt zur eigenen Übersicht: Dort steht, was der Kaffee gekostet hat
    # und ob noch etwas zu bezahlen ist.
    st.switch_page("my_coffee.py")

with st.expander("Kennwort vergessen?"):
    st.markdown(
        f"Die App verschickt keine E-Mails. Wenden Sie sich an "
        f"{st.secrets.admins['technik']}: Sie erhalten einen Link, "
        "über den Sie ein neues Kennwort vergeben können."
    )
st.subheader("So funktioniert es:")

st.markdown(
    f"""
    1. Lassen Sie sich von {st.secrets.admins['technik']} ein Konto anlegen. Sie bekommen dann einen Link, über den Sie Ihr Kennwort vergeben.
    2. Tragen Sie jeden Kaffee in dieses Tool ein, den Sie trinken.
    3. Erhalten Sie am Monatsende eine Abrechnung und zahlen Sie Ihren Anteil.
    
    __Warum digital?__ Die Abrechnung macht keinen Aufwand und Sie haben jederzeit einen Überblick über Ihre Kaffeeausgaben.

    Ein Kaffee kostet € 1,– für Gäste und € 0,25 für Mitglieder, die sich an der Monatsmiete beteiligen. Wenn Sie Mitglied werden wollen, wenden Sie sich an {st.secrets.admins['rechnung']}.
""",
    unsafe_allow_html=True,
)
st.expander("Datenschutz").markdown(
    f"Diese App speichert nur die Daten, die Sie eingeben. Die Daten werden ausschließlich zum Aufteilen der Unkosten für die Kaffeemaschine im 3. OG verwendet. Die Daten sind auf einem Server beim deutschen Anbieter Hetzner in Nürnberg gespeichert. Der Zugriff auf die Daten ist nur für die Administratoren der Kaffeekasse möglich. Sie können jederzeit einen vollständigen Einblick in Ihre Daten erhalten und die Löschung Ihrer Daten verlangen. Bitte wenden Sie sich dazu an {st.secrets.admins['technik']}."
)