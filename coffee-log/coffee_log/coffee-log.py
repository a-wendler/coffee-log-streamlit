import streamlit as st
import sqlite3
from datetime import datetime

# Initialize the database
conn = sqlite3.connect('coffee_counter.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        name TEXT,
        status TEXT,
        email TEXT
    )
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS coffee_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
''')
conn.commit()

# Function to add a new user
def add_user(code, name, email):
    try:
        c.execute('INSERT INTO users (code, name, email) VALUES (?, ?, ?)', (code, name, email))
        conn.commit()
        st.success(f"Nutzer {name} erfolgreich hinzugefügt!")
    except sqlite3.IntegrityError:
        st.error("Wählen Sie ein anderes Kennwort.")

# Function to log a coffee
def log_coffee(code):
    c.execute('SELECT id FROM users WHERE code = ?', (code,))
    user = c.fetchone()
    if user:
        user_id = user[0]
        timestamp = datetime.now().isoformat()
        c.execute('INSERT INTO coffee_log (user_id, timestamp) VALUES (?, ?)', (user_id, timestamp))
        conn.commit()
        st.success("Ihr Kaffee wurde eingetragen!")
    else:
        st.error("Ungültiges Kennwort!")

# Function to get monthly overview
def get_monthly_overview():
    c.execute('''
        SELECT users.name, COUNT(coffee_log.id) as coffee_count
        FROM coffee_log
        JOIN users ON coffee_log.user_id = users.id
        WHERE strftime('%Y-%m', coffee_log.timestamp) = strftime('%Y-%m', 'now')
        GROUP BY users.name
    ''')
    return c.fetchall()

# Streamlit app layout
st.title("Coffee Counter")

menu = ["Willkommen", "Kaffee trinken", "Registrieren", "Monatsabrechnung"]
choice = st.sidebar.selectbox("Menü", menu)

if choice == "Willkommen":
    st.subheader("So funktioniert es:")
    st.markdown("""Die Kaffeemaschine wird von einer Gruppe von Kolleg/-innen gemietet.

Wer sich an der Miete beteiligt, bezahlt einen monatlichen Grundbetrag von derzeit € 12 und pro Tasse Kaffee 25 ct.
                
Wer als Gast mittrinkt, zahlt € 1 pro Kaffee.

""")
if choice == "Kaffee trinken":
    st.subheader("Kaffee trinken")
    code = st.text_input("Geben Sie Ihr Kennwort ein.")
    if st.button("Kaffee eintragen"):
        log_coffee(code)

elif choice == "Registrieren":
    st.subheader("Neuen Nutzer für die Kaffeeabrechnung hinzufügen")
    code = st.text_input("Vergeben Sie ein Kennwort")
    name = st.text_input("Ihr Name")
    email = st.text_input("E-Mail")
    if st.button("Registrieren"):
        add_user(code, name, email)

elif choice == "Monatsabrechnung":
    st.subheader("Monthly Coffee Overview")
    overview = get_monthly_overview()
    for user, count in overview:
        st.write(f"{user}: {count} coffees")

# Close the database connection
conn.close()
