import streamlit as st


def logout():
    del st.session_state.user
    st.rerun()

# Streamlit app layout

# Initialize the database
conn = st.connection("coffee_counter", type="sql")

# add logfile to logger
# logger.add("logs.log")

# menu_with_redirect()


# Seiten ohne Login
register = st.Page("register.py", title="Registrieren", icon=":material/assignment_ind:")
home = st.Page("home.py", title="Start", icon=":material/home:", default=True)
login_page = st.Page("login_page.py", title="Anmelden", icon=":material/login:")

# Seiten mit Login
logout_page = st.Page(logout, title="Abmelden", icon=":material/logout:")
my_coffee = st.Page("my_coffee.py", title="Meine Kaffeeübersicht", icon=":material/local_cafe:")

# Seiten als Admin
payments = st.Page("payments.py", title="Zahlungen", icon=":material/payments:")
abrechnung = st.Page("abrechnung.py", title="Abrechnung", icon=":material/attach_money:")
users = st.Page("users.py", title="Nutzer verwalten", icon=":material/people:")
konto = st.Page("account.py", title="Kontostand", icon=":material/account_balance:")
if "user" in st.session_state:
    standard_pages = [home, register]
else:
    standard_pages = [home, register, login_page]
admin_pages = [payments, abrechnung, users, konto]
login_pages = [my_coffee, logout_page, ]

# st.write(st.session_state)
st.title("☕ LSB Kaffeeabrechnung")

page_dict = {}

if "user" not in st.session_state:
    page_dict["Menü"] = standard_pages

if "user" in st.session_state:
    page_dict["Menü"] = standard_pages
    if "user" in st.session_state and st.session_state.user.admin == 1:
        page_dict["Admin"] = admin_pages
    page_dict["Persönlicher Bereich"] = login_pages


pg = st.navigation(page_dict)
pg.run()

