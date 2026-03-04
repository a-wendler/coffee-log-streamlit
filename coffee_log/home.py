import streamlit as st
from loguru import logger

from login import login
from api_client import post


def reset_password(email: str) -> bool:
    """Request password reset. Returns True if request was sent (even if email not found)."""
    try:
        post("/auth/reset-password", json={"email": email})
        return True
    except Exception as e:
        logger.error(f"Fehler beim Passwortreset: {e}")
        return False


def log_coffee(anzahl: int) -> bool:
    """Log coffee consumption. Returns True on success."""
    if "user" not in st.session_state:
        st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")
        return False
    try:
        post("/coffee", json={"anzahl": anzahl})
        logger.success(f"{anzahl} Kaffee(s) eingetragen von {st.session_state.user['name']}")
        return True
    except Exception as e:
        st.error(f"Beim Eintragen des Kaffees ist ein Fehler aufgetreten: {e}")
        logger.error(f"Kaffee konnte nicht eingetragen werden: {e}")
        return False


st.subheader("Kaffee trinken")
with st.form(key="log_coffee", clear_on_submit=True):
    anzahl = st.select_slider(
        "Wieviele Tassen Kaffee wollen Sie eintragen?",
        options=list(range(1, 6)),
        key="anzahl_slider",
    )
    if "user" in st.session_state:
        submit = st.form_submit_button("Kaffee eintragen", type="primary")
    else:
        code = st.text_input(
            "Geben Sie Ihr Kennwort ein.", key="code_input", type="password"
        )
        submit = st.form_submit_button("Kaffee eintragen", type="primary")

if submit:
    if "user" in st.session_state:
        if log_coffee(st.session_state.anzahl_slider):
            st.success("Ihr Kaffee wurde eingetragen!")
            st.rerun()
    else:
        if "code_input" in st.session_state and login(st.session_state.code_input):
            if log_coffee(st.session_state.anzahl_slider):
                st.success("Ihr Kaffee wurde eingetragen!")
            st.rerun()
        else:
            st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")

with st.expander("Kennwort vergessen?"):
    st.subheader("Kennwort zurücksetzen")
    email = st.text_input("Geben Sie Ihre E-Mail-Adresse ein:")
    if st.button("Kennwort zurücksetzen"):
        if reset_password(email):
            st.success(
                f"Ein Link zum Zurücksetzen Ihres Kennworts wurde an {email} gesendet."
            )
        else:
            st.error("Fehler beim Zurücksetzen des Passwortes!")

st.subheader("So funktioniert es:")
try:
    admins = st.secrets.admins
    rechnung = admins.get("rechnung", "den Administrator")
except Exception:
    rechnung = "den Administrator"
st.markdown(
    f"""
1. Registrieren Sie sich links im Menü.
2. Tragen Sie jeden Kaffee in dieses Tool ein, den Sie trinken.
3. Erhalten Sie am Monatsende eine Abrechnung und zahlen Sie Ihren Anteil.

__Warum digital?__ Die Abrechnung macht keinen Aufwand und Sie haben jederzeit einen Überblick über Ihre Kaffeeausgaben.

Ein Kaffee kostet € 1,– für Gäste und € 0,25 für Mitglieder, die sich an der Monatsmiete beteiligen. Wenn Sie Mitglied werden wollen, registrieren Sie sich hier und wenden Sie sich an {rechnung}.
""",
    unsafe_allow_html=True,
)
try:
    technik = st.secrets.admins.get("technik", "den Administrator")
except Exception:
    technik = "den Administrator"
st.expander("Datenschutz").markdown(
    f"Diese App speichert nur die Daten, die Sie eingeben. Die Daten werden ausschließlich zum Aufteilen der Unkosten für die Kaffeemaschine im 3. OG verwendet. Die Daten sind auf einem Server beim deutschen Anbieter Hetzner in Nürnberg gespeichert. Der Zugriff auf die Daten ist nur für die Administratoren der Kaffeekasse möglich. Sie können jederzeit einen vollständigen Einblick in Ihre Daten erhalten und die Löschung Ihrer Daten verlangen. Bitte wenden Sie sich dazu an {technik}."
)
