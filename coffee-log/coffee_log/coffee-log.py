import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

monatsmiete = 215
kaffeepreis_mitglied = 0.25
kaffeepreis_gast = 1.0

# Initialize the database
conn = sqlite3.connect('coffee_counter.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        mitglied INTEGER,
        email TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS coffee_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        anzahl INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
conn.commit()

# Function to add a new user
def add_user(code, name, email):
    try:
        c.execute('INSERT INTO users (code, name, email, mitglied) VALUES (?, ?, ?, ?)', (code, name, email, 0))
        conn.commit()
        st.success(f"Nutzer {name} erfolgreich hinzugefügt!")
        st.info('Um getrunkenen Kaffee einzutragen, wählen Sie links aus dem Menü »Kaffee trinken«.')
    except sqlite3.IntegrityError:
        st.error("Wählen Sie ein anderes Kennwort.")

# Function to log a coffee
def log_coffee(code, anzahl):
    c.execute('SELECT id FROM users WHERE code = ?', (code,))
    user = c.fetchone()
    if user:
        user_id = user[0]
        timestamp = datetime.now().isoformat()
        c.execute('INSERT INTO coffee_log (user_id, timestamp, anzahl) VALUES (?, ?, ?)', (user_id, timestamp, anzahl))
        conn.commit()
        st.success("Ihr Kaffee wurde eingetragen!")
    else:
        st.error("Ungültiges Kennwort!")

# Function to edit user data
def edit_user_data():
    c.execute('SELECT * FROM users')
    users = c.fetchall()
    df = pd.DataFrame(users, columns=['id', 'code', 'name', 'mitglied', 'email'])
    
    edited_df = st.data_editor(df, column_config={
        "mitglied": st.column_config.CheckboxColumn(
            "Mitglied",
            help="Ist die Person zahlendes Mitglied der Mietergemeinschaft?",
            default=False,
        )
    }, num_rows="dynamic", key='data_editor')
    
    if st.button('Änderungen speichern'):
        for index, row in edited_df.iterrows():
            c.execute('''
                UPDATE users
                SET code = ?, name = ?, mitglied = ?, email = ?
                WHERE id = ?
            ''', (row['code'], row['name'], row['mitglied'], row['email'], row['id']))
        conn.commit()
        st.success("Änderungen wurden gespeichert!")

def get_subscription_fee():
    # Get the number of members
    c.execute('SELECT COUNT(*) FROM users WHERE mitglied = 1')
    num_members = c.fetchone()[0]
    if num_members == 0:
        retun = 0
    else:
        return monatsmiete / num_members

def calculate_monthly_balance():
    subscription_fee = get_subscription_fee()

    # Get the coffee consumption and calculate the balance
    c.execute('''
        SELECT users.name, users.mitglied, SUM(coffee_log.anzahl) as coffee_count
        FROM coffee_log
        JOIN users ON coffee_log.user_id = users.id
        WHERE strftime('%Y-%m', coffee_log.timestamp) = strftime('%Y-%m', 'now')
        GROUP BY users.name, users.mitglied
    ''')
    user_balances = c.fetchall()

    balances = []
    for name, mitglied, coffee_count in user_balances:
        if mitglied == 1:
            coffee_cost = coffee_count * kaffeepreis_mitglied
            total_cost = coffee_cost + subscription_fee
            balances.append((name, coffee_count, subscription_fee, coffee_cost, total_cost))

        else:
            total_cost = coffee_count * kaffeepreis_gast
            balances.append((name, coffee_count, 0, total_cost, total_cost))
        
    balance_df = pd.DataFrame(balances, columns=['Name', 'Anzahl Kaffees', 'Grundbetrag', 'Kaffeekosten', 'Gesamtkosten'])
    return balance_df
    

# Streamlit app layout
st.title("Coffee Counter")
if 'user' not in st.session_state:
    st.session_state['user'] = None
st.write(st.session_state['user'])

menu = ["Willkommen", "Kaffee trinken", "Registrieren", "Monatsabrechnung", "Nutzer bearbeiten"]
choice = st.sidebar.selectbox("Menü", menu)

if choice == "Willkommen":
    st.subheader("So funktioniert es:")
    st.markdown(f"""Die Kaffeemaschine wird von einer Gruppe von Kolleg/-innen gemietet.

Wer sich an der Miete beteiligt, bezahlt einen __monatlichen Grundbetrag__ von derzeit € {get_subscription_fee()} und pro Tasse Kaffee 25 ct.
                
Wer als Gast mittrinkt, zahlt € 1 pro Kaffee.

""")
if choice == "Kaffee trinken":
    st.subheader("Kaffee trinken")
    anzahl = st.select_slider('Wieviele Tassen Kaffee wollen Sie eintragen?', options=list(range(1,6)))
    code = st.text_input("Geben Sie Ihr Kennwort ein.")
    if st.button("Kaffee eintragen"):
        st.session_state['user'] = code
        log_coffee(code, anzahl)

elif choice == "Registrieren":
    st.subheader("Neuen Nutzer für die Kaffeeabrechnung hinzufügen")
    code = st.text_input("Vergeben Sie ein Kennwort")
    name = st.text_input("Ihr Name")
    email = st.text_input("E-Mail")
    if st.button("Registrieren"):
        add_user(code, name, email)

elif choice == "Monatsabrechnung":
    balance_df = calculate_monthly_balance()
    st.dataframe(balance_df)

elif choice == "Nutzer bearbeiten":
    st.subheader("Nutzer bearbeiten")
    edit_user_data()

# Close the database connection
conn.close()