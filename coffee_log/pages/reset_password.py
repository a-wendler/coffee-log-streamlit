"""
Modul zum Vergeben eines neuen Passwortes, wenn zuvor ein reset_token angefordert wurde.
"""

import time
from hashlib import sha256

import streamlit as st
from sqlalchemy import select

from models import User


def set_new_password(token):
    """Check if reset_key is valid and ask user for new password."""
    with conn.session as session:
        try:
            user = session.scalar(
                select(User).where(User.token == token, User.status == "active")
            )
            if user:
                new_password = st.text_input("Neues Kennwort", type="password")
                if st.button("Neues Kennwort speichern"):
                    user.code = sha256(new_password.encode("utf-8")).hexdigest()
                    user.token = None
                    session.commit()

                    st.markdown(
                        f"""Kennwort wurde geändert! Gehen Sie <a href="https://lsbkaffee.streamlit.app" target="_self">zurück zur Startseite</a>.""",
                        unsafe_allow_html=True,
                    )
                    st.query_params.clear()
        except:
            st.error("Ungültiger Link!")


# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

if "token" in st.query_params:
    if st.query_params.token.startswith("reset_"):
        set_new_password(st.query_params.token)
else:
    st.error("Ungültiger Link!")
