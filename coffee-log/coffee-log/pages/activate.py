"""Module to activate user account via query parameter token."""
import time

import streamlit as st
from models import User

def activate(token):
    """Check if token is valid and activate user."""
    with conn.session as session:
        #try:
        user = session.query(User).filter(User.token == token).first()
        if user:
            user.status = 'active'
            user.token = None
            session.commit()
            st.success("Ihr Konto wurde aktiviert! Sie werden zur Startseite weitergeleitet.")
            st.query_params.clear()
        #except:
            #st.error("Ein Fehler ist aufgetreten!")

# Streamlit app layout

# Initialize the database
conn = st.connection('coffee_counter', type='sql')

if 'token' in st.query_params:
    if st.query_params.token.startswith('activate_'):
        activate(st.query_params.token)

else:
    st.error("Ungültiger Link!")

time.sleep(3)
st.switch_page("app.py")
