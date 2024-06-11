from datetime import datetime
import pandas as pd
import streamlit as st
from menu import menu_with_redirect
from pages.monatsuebersicht import get_first_days_of_last_six_months
from models import Log, User
from sqlalchemy import select, extract

def abrechnung(datum):
    with conn.session as session:

        logs = session.execute(select(Log).filter(extract('month', Log.ts) == datum.month, extract('year', Log.ts) == datum.year)).all()
        mitglieder_kaffees = []
        gast_kaffees = []
        for log in logs:
            if log[0].user.mitglied == 1:
                mitglieder_kaffees.append({'Datum': log[0].ts, 'Anzahl': log[0].anzahl})
            if log[0].user.mitglied == 0:
                gast_kaffees.append({'Datum': log[0].ts, 'Anzahl': log[0].anzahl})
        logs_mitglieder = pd.DataFrame().from_records(mitglieder_kaffees)
        logs_gaeste = pd.DataFrame().from_records(gast_kaffees)

        st.write('Mitgliederkaffees:', logs_mitglieder.Anzahl.sum())
        st.write('Gastkaffees:', logs_gaeste.Anzahl.sum())
        st.write('Gesamtkaffees:', logs_mitglieder.Anzahl.sum() + logs_gaeste.Anzahl.sum())
menu_with_redirect()

# Streamlit app layout

conn = st.connection('coffee_counter', type='sql')
st.subheader("Abrechnung")

uebersetzungen = {'January':'Januar', 'February':'Februar', 'March':'März', 'April':'April', 'May':'Mai', 'June':'Juni', 'July':'Juli', 'August':'August', 'September':'September', 'October':'Oktober', 'November':'November', 'December':'Dezember'}
monatsliste = get_first_days_of_last_six_months()
datum = st.selectbox('Abrechnungsmonat', monatsliste, format_func=lambda x: uebersetzungen[x.strftime('%B')]+ ' ' + x.strftime('%Y'))
st.write(datum)
if datum:
    abrechnung(datum)