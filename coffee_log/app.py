from hashlib import sha256

import streamlit as st
from sqlalchemy import select
from loguru import logger

from database.models import User
from db import get_connection


def logout():
    del st.session_state.user
    st.rerun()


def clear_params():
    st.query_params.clear()


def tokens():
    if "token" in st.query_params:
        if st.query_params.token.startswith("reset_"):
            set_new_password()
        elif st.query_params.token.startswith("activate_"):
            activate()
        else:
            st.error("Ungültiger Link!")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()


def activate():
    """Kennwort vergeben und damit das eingeladene Konto aktivieren.

    Admins legen Konten ohne Kennwort an. Erst über den Einladungslink vergibt
    die eingeladene Person selbst eines; vorher steht das Konto auf "new" und
    der Login funktioniert nicht.
    """
    with conn.session as session:
        user = session.scalar(
            select(User).where(
                User.token == st.query_params.token, User.status == "new"
            )
        )
        if not user:
            st.error("Ungültiger Link!")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()
            return

        st.subheader("Konto aktivieren")
        st.write(
            f"Willkommen, {user.vorname} {user.name}! "
            "Bitte vergeben Sie ein Kennwort, mit dem Sie sich künftig anmelden."
        )
        with st.form(key="aktivieren"):
            kennwort = st.text_input("Kennwort", type="password")
            bestaetigung = st.text_input("Kennwort bestätigen", type="password")
            speichern = st.form_submit_button("Konto aktivieren", type="primary")

        if not speichern:
            return
        if not kennwort:
            st.error("Bitte geben Sie ein Kennwort ein.")
            return
        if kennwort != bestaetigung:
            st.error("Die Kennworte stimmen nicht überein.")
            return

        try:
            user.code = sha256(kennwort.encode("utf-8")).hexdigest()
            user.status = "active"
            user.token = None
            session.commit()
            st.success(
                "Ihr Konto wurde aktiviert! Sie können sich jetzt mit Ihrem Kennwort anmelden."
            )
            logger.success(f"Konto {user.id} aktiviert.")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()
        except Exception as e:
            session.rollback()
            # Das Kennwort ist zugleich der Login-Schlüssel und muss deshalb
            # eindeutig sein: ein bereits vergebenes lässt sich nicht speichern.
            logger.error(f"Fehler beim Aktivieren des Accounts: {e}")
            st.error(
                "Das Kennwort konnte nicht gespeichert werden. Bitte versuchen Sie es mit einem anderen Kennwort."
            )


def set_new_password():
    """Neues Kennwort über den Reset-Link vergeben.

    Den Link erzeugt ein Admin unter "Nutzer verwalten" und gibt ihn selbst
    weiter; die App verschickt keine E-Mails.
    """
    with conn.session as session:
        user = session.scalar(
            select(User).where(
                User.token == st.query_params.token, User.status == "active"
            )
        )
        if not user:
            st.error("Ungültiger Link!")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()
            return

        st.subheader("Neues Kennwort vergeben")
        st.write(f"Hallo, {user.vorname} {user.name}!")
        with st.form(key="neues_kennwort"):
            kennwort = st.text_input("Neues Kennwort", type="password")
            bestaetigung = st.text_input("Kennwort bestätigen", type="password")
            speichern = st.form_submit_button("Kennwort speichern", type="primary")

        if not speichern:
            return
        if not kennwort:
            st.error("Bitte geben Sie ein Kennwort ein.")
            return
        if kennwort != bestaetigung:
            st.error("Die Kennworte stimmen nicht überein.")
            return

        try:
            user.code = sha256(kennwort.encode("utf-8")).hexdigest()
            user.token = None
            session.commit()
            st.success("Ihr Kennwort wurde geändert!")
            logger.success(f"Kennwort für User {user.id} erfolgreich geändert.")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()
        except Exception as e:
            session.rollback()
            # Das Kennwort ist zugleich der Login-Schlüssel und muss deshalb
            # eindeutig sein: ein bereits vergebenes lässt sich nicht speichern.
            logger.error(f"Fehler beim Zurücksetzen des Kennworts: {e}")
            st.error(
                "Das Kennwort konnte nicht gespeichert werden. Bitte versuchen Sie es mit einem anderen Kennwort."
            )


# Streamlit app layout

# Initialize the database
conn = get_connection()

# add logfile to logger
# logger.add("logs.log")


# Seiten ohne Login
home = st.Page("home.py", title="Start", icon=":material/home:", default=True)
login_page = st.Page("login_page.py", title="Anmelden", icon=":material/login:")

# Seiten mit Login
logout_page = st.Page(logout, title="Abmelden", icon=":material/logout:")
my_coffee = st.Page(
    "my_coffee.py", title="Meine Kaffeeübersicht", icon=":material/local_cafe:"
)

# Seiten als Admin
payments = st.Page("payments.py", title="Zahlungen", icon=":material/payments:")
abrechnung = st.Page(
    "abrechnung.py", title="Abrechnung", icon=":material/attach_money:"
)
guthaben_test = st.Page("guthaben_test.py", title="Guthaben Test")
users = st.Page("users.py", title="Nutzer verwalten", icon=":material/people:")
konto = st.Page("account.py", title="Kontostand", icon=":material/account_balance:")
mietzahlungen = st.Page(
    "mietzahlungen.py", title="Mietzahlungen", icon=":material/attach_money:"
)
if "user" in st.session_state:
    standard_pages = [home]
else:
    standard_pages = [home, login_page]
admin_pages = [payments, abrechnung, users, konto, mietzahlungen]
login_pages = [
    my_coffee,
    logout_page,
]
st.title("☕ LSB Kaffeeabrechnung")

page_dict = {}

if "token" in st.query_params:
    pg = st.navigation([st.Page(tokens)])

else:
    page_dict["Menü"] = standard_pages
    if "user" in st.session_state:
        if st.session_state.user.admin == 1:
            page_dict["Admin"] = admin_pages
        page_dict["Persönlicher Bereich"] = login_pages
    pg = st.navigation(page_dict, position="sidebar", expanded=False)

pg.run()
