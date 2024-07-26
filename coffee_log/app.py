import streamlit as st
from loguru import logger

from database.models import User
from menu import menu_with_redirect

# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

# add logfile to logger
# logger.add("logs.log")

menu_with_redirect()
