from models import User
from hashlib import sha256
import streamlit as st
from loguru import logger


def check_user(conn):
    if "code_input" in st.session_state:
        if len(st.session_state.code_input) > 0:
            pwd = st.session_state.code_input
    if "code_login" in st.session_state:
        if len(st.session_state.code_login) > 0:
            pwd = st.session_state.code_login
    with conn.session as session:
        try:
            user = (
                session.query(User)
                .filter(
                    User.code == sha256(pwd.encode("utf-8")).hexdigest(),
                    User.status == "active",
                )
                .first()
            )
            st.session_state.current_user["name"] = user.name
            st.session_state.current_user["vorname"] = user.vorname
            st.session_state.current_user["id"] = user.id
            if user.admin:
                st.session_state.current_user["role"] = "admin"
            else:
                st.session_state.current_user["role"] = "user"
            st.session_state.user = user
        except Exception as e:
            logger.error(f"Login error: {e}")
            st.error("Fehler beim Login!")


# conn = st.connection("coffee_counter", type="sql")
