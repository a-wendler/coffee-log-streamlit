import streamlit as st
from sqlalchemy import create_engine

from database.models import Base
from login import check_user

# db_url = f"{st.secrets.connections.coffee_counter["dialect"]}+{st.secrets.connections.coffee_counter["driver"]}://{st.secrets.connections.coffee_counter["username"]}:{st.secrets.connections.coffee_counter["password"]}@{st.secrets.connections.coffee_counter["host"]}:{st.secrets.connections.coffee_counter["port"]}/{st.secrets.connections.coffee_counter["database"]}"
db_url = "sqlite:///coffee.db"


def setup_db():
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)


def logout():
    del st.session_state.user
    st.switch_page("app.py")


def authenticated_menu():
    # Show a navigation menu for authenticated users
    st.sidebar.title("LSB Kaffeeabrechnung DEV")
    st.sidebar.page_link("pages/home.py", label="Start")
    st.sidebar.page_link("pages/monatsuebersicht.py", label="Monatsübersicht")
    if st.session_state.user.admin == 1:
        st.sidebar.page_link("pages/users.py", label="Nutzer verwalten")
        st.sidebar.page_link(
            "pages/abrechnung.py",
            label="Abrechnung",
        )
        st.sidebar.page_link(
            "pages/payments.py",
            label="Zahlungen",
        )
        st.sidebar.page_link(
            "pages/account.py",
            label="Kontoübersicht",
        )
        st.sidebar.divider()
        setup = st.sidebar.button("Datenbank initialisieren")
        if setup:
            setup_db()
    st.sidebar.divider()
    st.sidebar.page_link("pages/my_coffee.py", label="Meine Kaffeeübersicht")
    st.sidebar.write(
        f"Eingeloggt als: {st.session_state.user.vorname} {st.session_state.user.name}"
    )

    if st.sidebar.button("Logout"):
        logout()


def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.title("LSB Kaffeeabrechnung DEV")
    st.sidebar.page_link("pages/home.py", label="Start")
    st.sidebar.page_link("pages/register.py", label="Registrieren")
    st.sidebar.divider()
    st.sidebar.write("Nicht eingeloggt")
    setup = st.sidebar.button("Datenbank initialisieren")
    if setup:
        setup_db()
    with st.sidebar.popover("Login"):
        with st.form(key="login_form", clear_on_submit=True):
            code_login = st.text_input("Kennwort", type="password", key="code_login")
            button = st.form_submit_button("Login", on_click=check_user, args=(conn,))
        if button:
            st.sidebar.success("Erfolgreich eingeloggt!")
    st.sidebar.page_link("pages/test_data.py", label="Test Daten")


def menu():
    # Determine if a user is logged in or not, then show the correct
    # navigation menu
    if "user" not in st.session_state:
        unauthenticated_menu()
        return
    
    authenticated_menu()


def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to
    # render the navigation menu
    if "user" not in st.session_state:
        st.switch_page("pages/home.py")
    menu()

conn = st.connection("coffee_counter", type="sql")