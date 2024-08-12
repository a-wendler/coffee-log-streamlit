from hashlib import sha256

import streamlit as st
from sqlalchemy import select
from loguru import logger

from database.models import User


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
    """Check if token is valid and activate user."""
    with conn.session as session:
        try:
            user = session.scalar(
                select(User).where(User.token == st.query_params.token)
            )
            if user:
                user.status = "active"
                user.token = None
                session.commit()
                st.success("Ihr Konto wurde aktiviert!")
            else:
                st.error("Ungültiger Link!")
                back = st.button("Zurück zur Startseite", on_click=clear_params)
                if back:
                    st.query_params.clear()
        except Exception as e:
            session.rollback()
            st.error(
                "Fehler beim Aktivieren des Accounts. Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator."
            )
            logger.error(f"Fehler beim Aktivieren des Accounts: {e}")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()


def set_new_password():
    """Check if reset_key is valid and ask user for new password."""
    with conn.session as session:
        try:
            user = session.scalar(
                select(User).where(
                    User.token == st.query_params.token, User.status == "active"
                )
            )
            # st.write(user)
            if user:
                new_password = st.text_input("Neues Kennwort", type="password")
                if st.button("Neues Kennwort speichern"):
                    user.code = sha256(new_password.encode("utf-8")).hexdigest()
                    user.token = None
                    session.commit()

                    st.write("Kennwort wurde geändert!")
                    logger.success(f"Passwort für User {user.id} erfolgreich geändert.")
                    back = st.button("Zurück zur Startseite", on_click=clear_params)
                    if back:
                        st.query_params.clear()

            else:
                st.error("Ungültiger Link!")
                back = st.button("Zurück zur Startseite", on_click=clear_params)
                if back:
                    st.query_params.clear()
        except Exception as e:
            session.rollback()
            st.error(
                "Fehler beim Zurücksetzen des Passworts. Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator."
            )
            logger.error(f"Fehler beim Zurücksetzen des Passworts: {e}")
            back = st.button("Zurück zur Startseite", on_click=clear_params)
            if back:
                st.query_params.clear()


# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

# add logfile to logger
# logger.add("logs.log")


# Seiten ohne Login
home = st.Page("home.py", title="Start", icon=":material/home:", default=True)
register = st.Page(
    "register.py", title="Registrieren", icon=":material/assignment_ind:"
)
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
if "user" in st.session_state:
    standard_pages = [home, register]
else:
    standard_pages = [home, register, login_page]
admin_pages = [payments, abrechnung, users, konto, guthaben_test]
login_pages = [
    my_coffee,
    logout_page,
]
passwort_reset_page = st.Page(set_new_password, title="Passwort zurücksetzen")

# st.write(st.session_state)
st.title("☕ LSB Kaffeeabrechnung")

page_dict = {}

if "token" in st.query_params:
    pg = st.navigation([st.Page(tokens)])

else:
    if "user" not in st.session_state:
        page_dict["Menü"] = standard_pages

    if "user" in st.session_state:
        page_dict["Menü"] = standard_pages
        if "user" in st.session_state and st.session_state.user.admin == 1:
            page_dict["Admin"] = admin_pages
        page_dict["Persönlicher Bereich"] = login_pages

if len(page_dict) > 0:
    pg = st.navigation(page_dict)

pg.run()
