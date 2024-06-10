import streamlit as st

import smtplib
from email.mime.text import MIMEText

def send_email(receiver_email, text, subject):
    # Configuration
    port, smtp_server, login, password, sender_email, reply_email = st.secrets.smtp

    # Create MIMEText object
    message = MIMEText(text, "plain")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Reply-To"] = reply_email

    # Send the email
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()  # Secure the connection
        server.login(login, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

def send_activation_email(receiver_email, token):
    subject = "Konto für LSB Kaffeeabrechnung aktivieren"
    text=f"""
    Herzlich willkommen bei der Kaffeeabrechnung der LSB! Bitte klicken Sie auf den folgenden Link, um Ihr Konto zu aktivieren:

    http://localhost:8501/activate/?token={token}

    Wenn Sie den Link nicht anklicken können, kopieren Sie ihn bitte in die Adresszeile Ihres Browsers.

    Sie erhalten Ihre Abrechnung immer zum Monatsende.

    Fragen zur Abrechnung beantwortet {st.secrets.admins['rechnung']}. Technische Fragen zum Abrechnungstool beantwortet {st.secrets.admins['technik']}.

    Lassen Sie sich Ihren Kaffee schmecken!
"""
    try:
        send_email(receiver_email, text, subject)
        return True
    except Exception as e:
        return e
