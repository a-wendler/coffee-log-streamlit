"""E-Mail-Versand für Aktivierung und Passwort-Reset.

Die Funktionen fangen Fehler bewusst *nicht* ab: wenn der Versand scheitert,
muss die aufrufende Seite das merken und eine Fehlermeldung anzeigen können.
Früher gaben sie die Exception als Rückgabewert zurück, wodurch jeder
fehlgeschlagene Versand als Erfolg gemeldet wurde.
"""

import smtplib
from email.mime.text import MIMEText

import streamlit as st
from loguru import logger


def send_email(receiver_email, text, subject):
    """Verschickt eine Mail. Wirft bei Fehlern eine Exception."""
    # Zugriff über die Schlüsselnamen, nicht über die Reihenfolge: sonst
    # entscheidet die Sortierung in secrets.toml, was Server und Passwort ist.
    smtp = st.secrets.smtp

    message = MIMEText(text, "plain")
    message["Subject"] = subject
    message["From"] = smtp["sender_email"]
    message["To"] = receiver_email
    message["Reply-To"] = smtp["reply_email"]

    with smtplib.SMTP(smtp["server"], smtp["port"]) as server:
        server.starttls()  # Verbindung absichern
        server.login(smtp["login"], smtp["password"])
        server.sendmail(smtp["sender_email"], receiver_email, message.as_string())


def send_activation_email(receiver_email, token):
    """Verschickt den Aktivierungslink. Wirft bei Fehlern eine Exception."""
    subject = "Konto für LSB-Kaffeeabrechnung aktivieren"
    text = f"""
    Herzlich willkommen bei der Kaffeeabrechnung der LSB! Bitte klicken Sie auf den folgenden Link, um Ihr Konto zu aktivieren:

    https://lsbkaffee.streamlit.app/?token={token}

    Wenn Sie den Link nicht anklicken können, kopieren Sie ihn bitte in die Adresszeile Ihres Browsers.

    Sie erhalten Ihre Abrechnung immer zum Monatsende.

    Fragen zur Abrechnung beantwortet {st.secrets.admins['rechnung']}. Technische Fragen zum Abrechnungstool beantwortet {st.secrets.admins['technik']}.

    Lassen Sie sich Ihren Kaffee schmecken!
"""
    send_email(receiver_email, text, subject)
    logger.success(f"Aktivierungsmail an {receiver_email} versandt.")


def send_reset_email(receiver_email, token):
    """Verschickt den Passwort-Reset-Link. Wirft bei Fehlern eine Exception."""
    subject = "Passwort für LSB-Kaffeeabrechnung zurücksetzen"
    text = f"""
    Klicken Sie auf den folgenden Link und geben Sie ein neues Passwort ein:

    https://lsbkaffee.streamlit.app/?token={token}

    Wenn Sie den Link nicht anklicken können, kopieren Sie ihn bitte in die Adresszeile Ihres Browsers.

    Fragen zur Abrechnung beantwortet {st.secrets.admins['rechnung']}. Technische Fragen zum Abrechnungstool beantwortet {st.secrets.admins['technik']}.

    Lassen Sie sich Ihren Kaffee schmecken!
"""
    send_email(receiver_email, text, subject)
    logger.success(f"Passwort-Reset-Mail an {receiver_email} versandt.")
