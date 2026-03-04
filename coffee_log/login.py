"""Login logic - calls API."""

import streamlit as st
from loguru import logger

from api_client import post


def login(code: str) -> bool:
    """Login with password. On success: sets st.session_state.user and access_token. Returns True if successful."""
    if not code or len(code) == 0:
        return False
    try:
        resp = post("/auth/login", json={"code": code})
        st.session_state.access_token = resp["access_token"]
        st.session_state.user = resp["user"]
        logger.success(f"Login: {resp['user']['name']}")
        return True
    except Exception as e:
        logger.error(f"Login error: {e}")
        st.error("Fehler beim Login!")
        return False


def is_logged_in() -> bool:
    """Check if user is logged in."""
    return "user" in st.session_state and st.session_state.user is not None
