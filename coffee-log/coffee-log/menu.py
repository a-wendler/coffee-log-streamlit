import streamlit as st
from sqlalchemy import create_engine

from models import Base

def setup_db():
    engine = create_engine('sqlite:///coffee_counter.db', echo=True)
    Base.metadata.create_all(engine)

def logout():
    del st.session_state.current_user
    st.switch_page("app.py")


def authenticated_menu():
    # Show a navigation menu for authenticated users
    st.sidebar.title("LSB Kaffeeabrechnung")
    st.sidebar.page_link("app.py", label="Start")
    st.sidebar.page_link("pages/monatsuebersicht.py", label="Monatsübersicht")
    if st.session_state.current_user['role'] in ["admin", "super-admin"]:
        st.sidebar.page_link("pages/users.py", label="Nutzer verwalten")
        st.sidebar.page_link(
            "pages/abrechnung.py",
            label="Abrechnung",
        )
        setup = st.sidebar.button("Datenbank initialisieren")
        if setup:
            setup_db()
    st.sidebar.divider()
    st.sidebar.write("Eingeloggt als:")
    st.sidebar.write(st.session_state.current_user['vorname'], ' ', st.session_state.current_user['name'])
    if st.sidebar.button("Logout"):
        logout()


def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.title("LSB Kaffeeabrechnung")
    st.sidebar.page_link("app.py", label="Start")
    st.sidebar.page_link("pages/register.py", label="Registrieren")
    st.sidebar.divider()
    st.sidebar.write("Nicht eingeloggt")


def menu():
    # Determine if a user is logged in or not, then show the correct
    # navigation menu
    if "role" not in st.session_state.current_user or st.session_state.current_user['role'] is None:
        unauthenticated_menu()
        return
    authenticated_menu()


def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to
    # render the navigation menu
    if "role" not in st.session_state.current_user or st.session_state.current_user['role'] is None:
        st.switch_page("app.py")
    menu()