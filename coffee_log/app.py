import streamlit as st
from loguru import logger

from api_client import get, post


def logout():
    if "user" in st.session_state:
        del st.session_state.user
    if "access_token" in st.session_state:
        del st.session_state.access_token
    st.rerun()


def clear_params():
    st.query_params.clear()


def tokens():
    if "token" not in st.query_params:
        return
    token = st.query_params.token
    if token.startswith("reset_"):
        set_new_password()
    elif token.startswith("activate_"):
        activate()
    else:
        st.error("Ungültiger Link!")
        back = st.button("Zurück zur Startseite", on_click=clear_params)
        if back:
            st.query_params.clear()


def activate():
    """Activate user account via API."""
    token = st.query_params.token
    try:
        get("/auth/activate", params={"token": token})
        st.success("Ihr Konto wurde aktiviert!")
    except Exception as e:
        st.error("Ungültiger Link!")
        logger.error(f"Fehler beim Aktivieren des Accounts: {e}")
    back = st.button("Zurück zur Startseite", on_click=clear_params)
    if back:
        st.query_params.clear()


def set_new_password():
    """Set new password via reset token."""
    token = st.query_params.token
    new_password = st.text_input("Neues Kennwort", type="password")
    if st.button("Neues Kennwort speichern"):
        if not new_password:
            st.error("Bitte geben Sie ein Kennwort ein.")
        else:
            try:
                post("/auth/set-password", json={"token": token, "new_password": new_password})
                st.success("Kennwort wurde geändert!")
                logger.success("Passwort erfolgreich geändert.")
            except Exception as e:
                st.error(
                    "Fehler beim Zurücksetzen des Passworts. Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator."
                )
                logger.error(f"Fehler beim Zurücksetzen des Passworts: {e}")
    back = st.button("Zurück zur Startseite", on_click=clear_params)
    if back:
        st.query_params.clear()


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
mietzahlungen = st.Page(
    "mietzahlungen.py", title="Mietzahlungen", icon=":material/attach_money:"
)

if "user" in st.session_state and st.session_state.user:
    standard_pages = [home, register]
else:
    standard_pages = [home, register, login_page]
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
    if "user" in st.session_state and st.session_state.user:
        if st.session_state.user.get("admin") == 1:
            page_dict["Admin"] = admin_pages
        page_dict["Persönlicher Bereich"] = login_pages
    pg = st.navigation(page_dict, position="sidebar", expanded=False)

pg.run()
