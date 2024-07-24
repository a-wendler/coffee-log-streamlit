import os
from hashlib import sha256
from datetime import datetime

import streamlit as st
from loguru import logger

from models import Log, User
from menu import menu_with_redirect
from pages.mail import send_reset_email

from login import check_user





# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

# add logfile to logger
# logger.add("logs.log")

if "current_user" not in st.session_state:
    st.session_state.current_user = {"name": "", "role": None}

menu_with_redirect()
