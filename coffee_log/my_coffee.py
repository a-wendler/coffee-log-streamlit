"""Persönliche Kaffeeübersicht."""

import pandas as pd
import streamlit as st

from database.queries import (
    get_monatslogs,
    get_monatspayments,
    get_rechnungen,
    get_saldo,
    hat_mietzahlung,
)
from db import get_connection
from helpers import get_first_days_of_last_six_months

UEBERSETZUNGEN = {
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


def monatsname(datum) -> str:
    return UEBERSETZUNGEN[datum.strftime("%B")] + " " + datum.strftime("%Y")


def widget_kaffee_anzahl(logs):
    """Tassenzahl des Monats und Aufstellung nach Tagen."""
    st.metric("getrunkene Tassen Kaffee", sum(log.anzahl for log in logs))
    if not logs:
        st.write("Sie haben in diesem Monat keinen Kaffee eingetragen.")
        return
    df = pd.DataFrame(
        [{"Datum": log.ts[:10], "Anzahl": log.anzahl} for log in logs]
    )
    st.dataframe(
        df.groupby("Datum")["Anzahl"].sum().reset_index(),
        column_config={
            "Datum": st.column_config.DatetimeColumn("Datum", format="DD.MM.YY")
        },
    )


def widget_payments(payments):
    """Einkäufe und Auszahlungen des Monats."""
    if not payments:
        st.write(
            "Sie haben in diesem Monat keine Einkäufe oder Auszahlungen abgerechnet."
        )
        return
    st.dataframe(
        [
            {
                "Datum": payment.ts,
                "Typ": payment.typ,
                "Betrag": payment.betrag,
                "Betreff": payment.betreff,
            }
            for payment in payments
        ],
        column_config={
            "Betrag": st.column_config.NumberColumn(format="€ %g"),
            "Datum": st.column_config.DatetimeColumn("Datum", format="DD.MM.YY"),
        },
    )


def widget_saldo(saldo, offene_rechnungen):
    """Guthaben bzw. offener Betrag – mit Zahlungshinweis, wenn etwas offen ist."""
    if saldo < 0:
        st.metric("offener Betrag", "€ " + str(saldo))
    elif saldo > 0:
        st.metric("Ihr Guthaben", "€ " + str(saldo))
    else:
        st.metric("Ihr Saldo ist ausgeglichen", "€ 0")

    # Die Zahlungsoptionen standen früher nur in der Rechnungs-E-Mail.
    if saldo < 0 or offene_rechnungen:
        st.info(f"**So können Sie zahlen**\n\n{st.secrets.ZAHLUNGSOPTIONEN}")


def widget_invoices(invoices):
    """Alle Rechnungen der angemeldeten Person."""
    if not invoices:
        st.write("Keine Rechnungen gefunden.")
        return
    st.dataframe(
        [
            {
                "Rechnungsmonat": invoice.monat,
                "Zahlbetrag": invoice.gesamtbetrag,
                "Kaffeekosten": invoice.kaffee_preis,
                "Kaffeeanzahl": invoice.kaffee_anzahl,
                "Einkäufe etc.": invoice.payment_betrag,
                "bezahlt": invoice.bezahlt,
            }
            for invoice in invoices
        ],
        column_config={
            "Betrag": st.column_config.NumberColumn("Rechnungsbetrag", format="€ %g"),
            "Rechnungsmonat": st.column_config.DatetimeColumn(
                "Rechnungsmonat", format="MMM YYYY"
            ),
            "Einkäufe etc.": st.column_config.NumberColumn(
                "Einkäufe etc.", format="€ %g"
            ),
            "bezahlt": st.column_config.DatetimeColumn(
                "bezahlt am", format="DD.MM.YYYY"
            ),
        },
    )


st.header("Meine Kaffeeübersicht")
conn = get_connection()

monate = get_first_days_of_last_six_months()
datum = st.selectbox("Abrechnungsmonat", monate, format_func=monatsname)

if datum:
    # Alle Daten der Seite in einer einzigen Session laden, danach nur noch
    # darstellen – so löst das Rendern keine weiteren Queries mehr aus.
    user_id = st.session_state.user.id
    with conn.session as session:
        logs = get_monatslogs(session, user_id, datum)
        payments = get_monatspayments(session, user_id, datum)
        miete_bezahlt = hat_mietzahlung(session, user_id, datum)
        saldo = get_saldo(session, user_id)
        invoices = get_rechnungen(session, user_id)

    with st.container(border=True):
        st.subheader("Kaffeeanzahl im ausgewählten Monat")
        widget_kaffee_anzahl(logs)
        st.subheader("Zahlungen im ausgewählten Monat")
        widget_payments(payments)
        st.subheader("Mietanteil")
        if miete_bezahlt:
            st.write("✅ Ihre Mietzahlung wurde diesen Monat bereits verbucht.")
        else:
            st.write("❌ Ihre Mietzahlung ist noch nicht eingegangen.")

    offene_rechnungen = [
        invoice for invoice in invoices if invoice.bezahlt is None
    ]

    st.subheader("Saldo insgesamt")
    widget_saldo(saldo, offene_rechnungen)
    st.divider()
    st.subheader("Meine Rechnungen")
    st.write(
        f"Rechnungen werden immer am Anfang eines Monats für den zurückliegenden Monat erstellt. Wenn Sie (z. B. wegen Urlaub) in einem Monat keinen Kaffee getrunken haben, wird auch keine Rechnung erstellt. Rechnungen gelten als bezahlt, sobald {st.secrets.admins.rechnung} den Rechnungseingang verbucht hat. Rechnungen mit einem negativen Betrag sind Guthaben. Solche Rechnungen sind immer automatisch als bezahlt markiert. Das Guthaben wird auf zukünftige Rechnungen angerechnet. Wenn Ihr Guthaben zu groß wird, können Sie sich das Guthaben bei {st.secrets.admins.rechnung} auszahlen lassen."
    )
    widget_invoices(invoices)
