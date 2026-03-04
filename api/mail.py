"""Email sending for API - no Streamlit dependency."""

import smtplib
from email.mime.text import MIMEText
from typing import Any


def send_email(
    receiver_email: str,
    text: str,
    subject: str,
    smtp_config: dict[str, Any],
) -> None:
    """Send email using provided SMTP config."""
    port = smtp_config.get("port", 587)
    smtp_server = smtp_config["host"]
    login = smtp_config["username"]
    password = smtp_config["password"]
    sender_email = smtp_config["email"]
    reply_email = smtp_config.get("reply_to", sender_email)

    message = MIMEText(text, "plain")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Reply-To"] = reply_email

    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()
        server.login(login, password)
        server.sendmail(sender_email, receiver_email, message.as_string())


def send_activation_email(
    receiver_email: str,
    token: str,
    app_url: str,
    admin_technik: str,
) -> None:
    """Send account activation email."""
    subject = "Konto für LSB-Kaffeeabrechnung aktivieren"
    text = f"""
Herzlich willkommen bei der Kaffeeabrechnung der LSB! Bitte klicken Sie auf den folgenden Link, um Ihr Konto zu aktivieren:

{app_url}/?token={token}

Wenn Sie den Link nicht anklicken können, kopieren Sie ihn bitte in die Adresszeile Ihres Browsers.

Sie erhalten Ihre Abrechnung immer zum Monatsende.

Fragen zur Abrechnung beantwortet der Administrator. Technische Fragen zum Abrechnungstool beantwortet {admin_technik}.

Lassen Sie sich Ihren Kaffee schmecken!
"""
    from api.config import settings

    smtp_config = {
        "host": settings.smtp_server,
        "port": settings.smtp_port,
        "username": settings.smtp_login,
        "password": settings.smtp_password,
        "email": settings.smtp_sender,
        "reply_to": settings.smtp_reply,
    }
    send_email(receiver_email, text, subject, smtp_config)


def send_invoice_email(
    receiver_email: str,
    receiver_name: str,
    receiver_vorname: str,
    monat_str: str,
    kaffee_anzahl: int,
    kaffee_preis: float,
    payment_betrag: float | None,
    gesamtbetrag: float,
    saldo: float,
    zahlungsoptionen: str,
) -> None:
    """Send invoice email."""
    subject = f"LSB Kaffeeabrechnung {monat_str}"
    text = f"""
Guten Tag {receiver_vorname} {receiver_name},
Ihre Kaffeeabrechnung für {monat_str}:

Getrunkene Tassen Kaffee: {kaffee_anzahl}
Preis für Kaffee: {kaffee_preis} €"""
    if payment_betrag:
        text += f"""
Einkäufe diesen Monat: {payment_betrag} €
"""
    if gesamtbetrag < kaffee_preis:
        if gesamtbetrag == 0:
            text += f"""
Ihr bestehendes Guthaben wurde mit den Kosten für diesen Monat verrechnet.

Sie müssen nichts überweisen.

Ihr aktuelles Guthaben beträgt: {saldo} €
"""
        if gesamtbetrag > 0:
            text += f"""
Ihr bestehendes Guthaben wurde mit den Kosten für diesen Monat verrechnet.

Sie müssen nur den Restbetrag von {gesamtbetrag} € überweisen.

{zahlungsoptionen}
"""
    if gesamtbetrag == kaffee_preis:
        text += f"""
=========================================================
Gesamtbetrag: {gesamtbetrag} €

{zahlungsoptionen}
"""
    from api.config import settings

    smtp_config = {
        "host": settings.smtp_server,
        "port": settings.smtp_port,
        "username": settings.smtp_login,
        "password": settings.smtp_password,
        "email": settings.smtp_sender,
        "reply_to": settings.smtp_reply,
    }
    send_email(receiver_email, text, subject, smtp_config)


def send_reset_email(
    receiver_email: str,
    token: str,
    app_url: str,
    admin_rechnung: str,
    admin_technik: str,
) -> None:
    """Send password reset email."""
    subject = "Passwort für LSB-Kaffeeabrechnung zurücksetzen"
    text = f"""
Klicken Sie auf den folgenden Link und geben Sie ein neues Passwort ein:

{app_url}/?token={token}

Wenn Sie den Link nicht anklicken können, kopieren Sie ihn bitte in die Adresszeile Ihres Browsers.

Fragen zur Abrechnung beantwortet {admin_rechnung}. Technische Fragen zum Abrechnungstool beantwortet {admin_technik}.

Lassen Sie sich Ihren Kaffee schmecken!
"""
    from api.config import settings

    smtp_config = {
        "host": settings.smtp_server,
        "port": settings.smtp_port,
        "username": settings.smtp_login,
        "password": settings.smtp_password,
        "email": settings.smtp_sender,
        "reply_to": settings.smtp_reply,
    }
    send_email(receiver_email, text, subject, smtp_config)
