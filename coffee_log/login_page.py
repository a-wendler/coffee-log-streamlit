import streamlit as st

from login import login

conn = st.connection("coffee_counter", type="sql")
with st.form(key="login_form", clear_on_submit=True):
    code_login = st.text_input("Kennwort", type="password", key="code_login")
    button = st.form_submit_button("Login", on_click=login, args=(conn,))
