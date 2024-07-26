import streamlit as st

from pages.monatsuebersicht import get_first_days_of_last_six_months
from menu import menu


def widget_kaffee_anzahl(datum, conn):
    st.metric(
        "getrunkene Tassen Kaffee",
        st.session_state.user.get_anzahl_monatskaffees(datum, conn),
    )


st.header("Meine Kaffeeübersicht")
menu()
conn = st.connection("coffee_counter", type="sql")
uebersetzungen = {
    "January": "Januar",
    "February": "Februar",
    "March": "März",
    "April": "April",
    "May": "Mai",
    "June": "Juni",
    "July": "Juli",
    "August": "August",
    "September": "September",
    "October": "Oktober",
    "November": "November",
    "December": "Dezember",
}
monate = get_first_days_of_last_six_months()
datum = st.selectbox(
    "Abrechnungsmonat",
    monate,
    format_func=lambda x: uebersetzungen[x.strftime("%B")] + " " + x.strftime("%Y"),
)

if datum:
    widget_kaffee_anzahl(datum, conn)
