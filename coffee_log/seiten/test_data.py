from datetime import datetime
from hashlib import sha256
import random

import streamlit as st

from database.models import User, Log


def test_data_user(conn):
    user_list = []
    for i in range(1, 19):
        # Mitglieder
        user_list.append(
            User(
                name=f"Name{i}",
                vorname=f"Vorname{i}",
                email=f"andre.wendler+{i}@gmail.com",
                code=sha256(f"user{i}".encode("utf-8")).hexdigest(),
                status="active",
                mitglied=1,
                ts=datetime.now().isoformat(),
            )
        )
        # Gäste
    for i in range(19, 40):
        user_list.append(
            User(
                name=f"Name{i}",
                vorname=f"Vorname{i}",
                email=f"andre.wendler+{i}@gmail.com",
                code=sha256(f"user{i}".encode("utf-8")).hexdigest(),
                status="active",
                mitglied=0,
                ts=datetime.now().isoformat(),
            )
        )
    user_list.append(
        User(
            name="Wendler",
            vorname="Andre",
            email="andre.wendler@gmail.com",
            code=sha256("wendler".encode("utf-8")).hexdigest(),
            status="active",
            admin=1,
            mitglied=1,
            ts=datetime.now().isoformat(),
        )
    )

    with conn.session as session:
        session.add_all(user_list)
        session.commit()


def test_data_log(conn):
    log_list = []
    for monat in range(1, 7):
        for user in range(1, 40):
            with conn.session as session:
                curr_user = session.query(User.mitglied).filter(User.id == user).first()
                if curr_user[0] == 1:
                    for tag in range(1, 21):
                        log_list.append(
                            Log(
                                anzahl=random.randint(1, 2),
                                user_id=user,
                                ts=datetime(2024, monat, tag, 10, 10),
                            )
                        )
                if curr_user[0] == 0:
                    for tag in range(1, 21, 3):
                        log_list.append(
                            Log(
                                anzahl=1,
                                user_id=user,
                                ts=datetime(2024, monat, tag, 10, 10),
                            )
                        )
    with conn.session as session:
        session.add_all(log_list)
        session.commit()

st.write("hello")

conn = st.connection("coffee_counter", type="sql")
# if 'database' in st.secrets.connections.coffee_counter:
#     if st.secrets.connections.coffee_counter['database'] == 'coffee':
#         pass
#     if st.secrets.connections.coffee_counter['database'] == 'coffee_test':
#         test_data_user(conn)
#         test_data_log(conn)
# elif 'url' in st.secrets.connections.coffee_counter:
test_data_user(conn)
test_data_log(conn)
