import streamlit as st
from datetime import datetime
import pandas as pd
from sqlalchemy import select
from menu import menu_with_redirect
from models import User

def get_first_days_of_last_six_months():
    # Get the current date
    current_date = datetime.now()
    
    # Initialize an empty list to store the first days
    first_days = []
    
    # Loop to get the first day of the last 6 months including the current month
    for i in range(6):
        # Calculate the month and year
        month = (current_date.month - i - 1) % 12 + 1
        year = current_date.year + (current_date.month - i - 1) // 12
        
        # Get the first day of the month
        first_day = datetime(year, month, 1)
        
        # Append the first day to the list
        first_days.append(first_day)
  
    return first_days

def monatsuebersicht():
    uebersetzungen = {'January':'Januar', 'February':'Februar', 'March':'März', 'April':'April', 'May':'Mai', 'June':'Juni', 'July':'Juli', 'August':'August', 'September':'September', 'October':'Oktober', 'November':'November', 'December':'Dezember'}
    monatsliste = get_first_days_of_last_six_months()
    monat = st.selectbox('Monat', monatsliste, format_func=lambda x: uebersetzungen[x.strftime('%B')]+ ' ' + x.strftime('%Y'))
    with conn.session as session:
        log_user = session.execute(select(User).where(User.id == st.session_state.current_user['id'])).scalar_one()        
        logliste = []
        for entry in log_user.logs:
            if datetime.fromisoformat(entry.ts).month == monat.month:
                ts_format = datetime.fromisoformat(entry.ts).strftime('%d.%m.%Y %H:%M')
                logliste.append({'Datum': ts_format, 'Anzahl': entry.anzahl})
        df = pd.DataFrame().from_records(logliste)
        df
        if len(df) > 0:
            st.write(f"Gesamtanzahl Kaffees im {uebersetzungen[monat.strftime('%B')]+ ' ' + monat.strftime('%Y')}: {df['Anzahl'].sum()}")

# Streamlit app layout
# Initialize the database
menu_with_redirect()
conn = st.connection('coffee_counter', type='sql')

st.subheader("Monatsübersicht")
monatsuebersicht()