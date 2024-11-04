import streamlit as st
from sqlalchemy import select, extract

from database.models import Mietzahlung, User
from helpers import get_first_days_of_last_six_months

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
    with conn.session as session:
        mietzahlungen = session.scalars(
            select(Mietzahlung).where(
                extract("month", Mietzahlung.monat) == datum.month,
                extract("year", Mietzahlung.monat) == datum.year,
            )
        )
        zahlungsliste = [zahlung.user_id for zahlung in mietzahlungen]

        mitglieder = session.scalars(
            select(User).where(User.mitglied == 1).order_by(User.name)
        )

        # monatsliste = {mitglied.id:(1 if mitglied.id in zahlungsliste else 0) for mitglied in mitglieder}
        monatsliste = {}
        
        for mitglied in mitglieder:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                        st.write(mitglied.name)
                
                if mitglied.id in zahlungsliste:    
                    with col2:
                        st.write("✅")
                else:
                    with col2:
                        st.button(
                            "Zahlung eintragen",
                            key=mitglied.id,
                            on_click=mitglied.mietzahlung_eintragen,
                            args=(
                                conn,
                                datum,
                            ),
                        )
