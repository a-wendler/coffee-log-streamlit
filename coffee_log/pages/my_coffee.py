import streamlit as st

from pages.monatsuebersicht import get_first_days_of_last_six_months
from menu import menu


def widget_kaffee_anzahl(datum, conn):
    st.metric(
        "getrunkene Tassen Kaffee",
        int(st.session_state.user.get_anzahl_monatskaffees(datum, conn),)
    )

def widget_payments(datum, conn):
    payments = st.session_state.user.get_payments(datum, conn)
    payment_list = []
    for payment in payments:
        payment_list.append(
            {
                "Betrag": payment.betrag,
                "Betreff": payment.betreff,
                "Typ": payment.typ,
                "Datum": payment.ts,
            }
        )
    if len(payment_list) == 0:
        return st.write("Keine Zahlungen in diesem Monat gefunden.")
    return st.dataframe(payment_list)

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
    st.subheader("Kaffeeanzahl")
    widget_kaffee_anzahl(datum, conn)
    st.subheader("Zahlungen")
    widget_payments(datum, conn)
