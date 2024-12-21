import streamlit as st
from contextlib import contextmanager
from sqlalchemy.pool import QueuePool
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from database.models import User
from decimal import Decimal


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    try:
        with conn.session as session:
            yield session
            # session.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def create_db_url():
    # Get database credentials from secrets.toml
    db_username = st.secrets.connections.coffee_counter["username"]
    db_password = st.secrets.connections.coffee_counter["password"]
    db_host = st.secrets.connections.coffee_counter["host"]
    db_port = st.secrets.connections.coffee_counter["port"]
    db_name = st.secrets.connections.coffee_counter["database"]

    # Construct database URL
    db_url = (
        f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    return db_url


conn = st.connection(
    "coffee_counter",
    type="sql",
    url=create_db_url(),
    pool_size=5,  # Base number of connections to maintain
    max_overflow=10,  # Allow up to 10 connections beyond pool_size
    pool_timeout=30,  # Seconds to wait before timing out
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_pre_ping=True,  # Verify connection validity before checkout
    poolclass=QueuePool,
)

with get_db_connection() as session:
    users = (
        session.scalars(
            select(User)
            .options(
                selectinload(User.payments),
                selectinload(User.invoices),
                selectinload(User.logs),
            )
            .order_by(User.name)
        )
    ).all()

    einzahlungen = 0
    einkaeufe = 0
    auszahlungen = 0
    korrekturen = 0
    offene_rechnungen = []
    offene_rechnungen_summe = 0
    mitgliederkaffees = 0
    gastkaffees = 0
    saldi = []
    summe_positiv = 0

    for user in users:
        for payment in user.payments:
            if payment.typ == "Einzahlung":
                einzahlungen += payment.betrag
            elif payment.typ == "Einkauf":
                einkaeufe -= payment.betrag
            elif payment.typ == "Auszahlung":
                auszahlungen += payment.betrag
            elif payment.typ == "Korrektur":
                korrekturen += payment.betrag

        for invoice in user.invoices:
            if invoice.bezahlt is None:
                offene_rechnungen.append(
                    {
                        "Datum": invoice.ts,
                        "Betrag": invoice.gesamtbetrag,
                        "Nutzer": invoice.user.name,
                    }
                )
                offene_rechnungen_summe += invoice.gesamtbetrag

        if user.mitglied:
            for log in user.logs:
                mitgliederkaffees += log.anzahl
        else:
            for log in user.logs:

                gastkaffees += log.anzahl

        saldo = user.get_saldo(conn)
        if saldo > 0:
            summe_positiv += saldo
        saldi.append(
            {
                "Name": user.name,
                "Vorname": user.vorname,
                "Mitglied": user.mitglied,
                "Saldo": saldo,
            }
        )

    mitgliedskosten = mitgliederkaffees * Decimal(st.secrets.KAFFEEPREIS_MITGLIED)
    gastkosten = gastkaffees * Decimal(st.secrets.KAFFEEPREIS_GAST)

    st.title("Kontoübersicht")

    col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Einzahlungen", "€ " + str(einzahlungen).replace(".", ","))
    st.metric("Auszahlungen", "€ " + str(auszahlungen).replace(".", ","))
    st.metric("Korrekturen", "€ " + str(korrekturen).replace(".", ","))
    st.metric(
        "Kassenstand",
        "€ " + str(einzahlungen + auszahlungen + korrekturen).replace(".", ","),
    )
    st.metric(
        "offene Rechnungen", "€ " + str(offene_rechnungen_summe).replace(".", ",")
    )

    st.metric("Einkäufe", "€ " + str(einkaeufe).replace(".", ","))

with col2:

    st.metric("Kaffeeanzahl Mitglieder", str(mitgliederkaffees))
    st.metric("Kaffeeanzahl Gäste", str(gastkaffees))
    st.metric("Kaffeeanzahl gesamt", str(mitgliederkaffees + gastkaffees))
    st.metric("Summe der Guthaben", "€ " + str(summe_positiv).replace(".", ","))
    st.metric(
        "Überschuss",
        "€ " + str(mitgliedskosten + gastkosten + einkaeufe).replace(".", ","),
    )

with col3:
    st.metric("Kaffeeumsatz Mitglieder", "€ " + str(mitgliedskosten).replace(".", ","))
    st.metric("Kaffeeumsatz Gäste", "€ " + str(gastkosten).replace(".", ","))
    st.metric(
        "Kaffeeumsatz gesamt",
        "€ " + str(mitgliedskosten + gastkosten).replace(".", ","),
    )

    # st.write(f"Einzahlungen: {einzahlungen}")
    # st.write(f"Einkäufe: {einkaeufe}")
    # st.write(f"Auszahlungen: {auszahlungen}")
    # st.write(f"Korrekturen: {korrekturen}")
    # st.write(f"Offene Rechnungen: {offene_rechnungen_summe}")
    # st.write(f"Mitgliederkaffees: {mitgliederkaffees}")
    # st.write(f"Gastkaffees: {gastkaffees}")

st.subheader("offene Rechnungen")
st.dataframe(
    offene_rechnungen,
    column_config={
        "Betrag": st.column_config.NumberColumn(format="€ %g"),
        "Datum": st.column_config.DatetimeColumn(format="DD.MM.YY"),
    },
)

st.subheader("Saldi der Nutzenden")
st.dataframe(
    saldi,
    column_config={"Saldo": st.column_config.NumberColumn(format="€ %g")},
)

st.write(
    "Ein positiver Saldo bedeutet, dass die Person Guthaben hat. Negativer Saldo bedeutet, dass Rechnungen offen sind. Kaffees des laufenden Monats für den noch keine Abrechnung gemacht wurde sind im individuellen Saldo nicht enthalten."
)
