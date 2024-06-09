import streamlit as st

import smtplib
from email.mime.text import MIMEText

# Configuration
port, smtp_server, login, password, sender_email, reply_email = **st.secrets.smtp

receiver_email = "andre.wendler@gmail.com"

# Plain text content
text = """\
Hi,
Check out the new post on the Mailtrap blog:
SMTP Server for Testing: Cloud-based or Local?
https://blog.mailtrap.io/2018/09/27/cloud-or-local-smtp-server/
Feel free to let us know what content would be useful for you!
"""

# Create MIMEText object
message = MIMEText(text, "plain")
message["Subject"] = "TEst Nr. 1 aus Python"
message["From"] = sender_email
message["To"] = receiver_email
message["Reply-To"] = reply_email

# Send the email
with smtplib.SMTP(smtp_server, port) as server:
    server.starttls()  # Secure the connection
    server.login(login, password)
    server.sendmail(sender_email, receiver_email, message.as_string())

st.write("Email sent!")