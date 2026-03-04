"""Module to register new users via API."""

import streamlit as st

from api_client import post


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r"^[\+\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


def add_user(code: str, name: str, vorname: str, email: str, code_confirm: str) -> bool:
    """Register new user via API. Returns True on success."""
    try:
        post(
            "/auth/register",
            json={
                "vorname": vorname,
                "name": name,
                "email": email,
                "code": code,
                "code_confirm": code_confirm,
            },
        )
        st.success(
            f"Nutzer {name} erfolgreich hinzugefügt! Eine E-Mail wurde an {email} gesendet. "
            "Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den Link in der E-Mail klicken."
        )
        return True
    except Exception as e:
        from api_client import APIError

        msg = e.detail if isinstance(e, APIError) and e.detail else str(e)
        st.error(msg or "Nutzer konnte nicht registriert werden.")
        return False


st.subheader("Neuen Nutzer für die Kaffeeabrechnung hinzufügen")
with st.form(key="add_user"):
    vorname = st.text_input("Vorname")
    name = st.text_input("Nachname")
    email = st.text_input("E-Mail")
    code = st.text_input("Kennwort", type="password")
    confirm_code = st.text_input("Kennwort bestätigen", type="password")
    st.write("Alle Felder sind Pflichtfelder.")
    submit = st.form_submit_button("Registrieren")

if submit:
    if not all([vorname, name, email, code, confirm_code]):
        st.error("Alle Felder sind Pflichtfelder.")
    elif not is_valid_email(email):
        st.error("Bitte geben Sie eine gültige E-Mail-Adresse ein.")
    elif code != confirm_code:
        st.error("Die Passworte stimmen nicht überein.")
    else:
        add_user(code, name, vorname, email, confirm_code)
