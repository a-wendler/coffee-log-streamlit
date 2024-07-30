from hashlib import sha256

import streamlit as st
from loguru import logger

from database.models import User


def login(conn):
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
            
            # st.session_state.current_user["name"] = user.name
            # st.session_state.current_user["vorname"] = user.vorname
            # st.session_state.current_user["id"] = user.id
            # if user.admin:
            #     st.session_state.current_user["role"] = "admin"
            # else:
            #     st.session_state.current_user["role"] = "user"
            if isinstance(user, User):
                st.session_state.user = user
                logger.success(f"Login: {user.name}")
        except Exception as e:
            logger.error(f"Login error: {e}")
            st.error("Fehler beim Login!")
    if "user" not in st.session_state:
        st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")