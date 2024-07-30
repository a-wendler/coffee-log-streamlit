"""
Module to activate user account via query parameter token.
"""

import time

import streamlit as st
from models import User
from sqlalchemy import select


def activate(token):
    """Check if token is valid and activate user."""
    with conn.session as session:
        # try:
        # user = session.query(User).filter(User.token == token).first()
        user = session.scalar(select(User).where(User.token == token))
        if user:
            user.status = "active"
            user.token = None
            session.commit()
            st.success(
                "Ihr Konto wurde aktiviert! Sie werden zur Startseite weitergeleitet."
            )
            st.query_params.clear()
        # except:
        # st.error("Ein Fehler ist aufgetreten!")


# Streamlit app layout

if "token" in st.query_params:
    if st.query_params.token.startswith("activate_"):
        conn = st.connection("coffee_counter", type="sql")
        activate(st.query_params.token)
else:
    st.error("Ungültiger Link!")

time.sleep(3)
st.switch_page("app.py")
