import streamlit as st

from login import login

with st.form(key="login_form", clear_on_submit=True):
    code_login = st.text_input("Kennwort", type="password", key="code_login")
    button = st.form_submit_button("Login")

if button and "code_login" in st.session_state:
    if login(st.session_state.code_login):
        st.rerun()
    else:
        st.error("Ungültiges Kennwort oder Nutzerkonto nicht aktiviert!")
