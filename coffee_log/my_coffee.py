import streamlit as st

from helper import get_first_days_of_last_six_months


def widget_kaffee_anzahl(datum, conn):
    st.metric(
        "getrunkene Tassen Kaffee",
        int(
            st.session_state.user.get_anzahl_monatskaffees(datum, conn),
        ),
    )


def widget_payments(datum, conn):
    payments = st.session_state.user.get_payments(datum, conn)
    payment_list = []
    for payment in payments:
        payment_list.append(
            {
                "Datum": payment.ts,
                "Typ": payment.typ,
                "Betrag": payment.betrag,
                "Betreff": payment.betreff,
            }
        )
    if len(payment_list) == 0:
        return st.write("Sie haben in diesem Monat keine Einkäufe oder Auszahlungen abgerechnet.")
    return payment_list


def widget_saldo():
    saldo = st.session_state.user.get_saldo(conn)
    if saldo < 0:
        st.metric(
            "offener Betrag",
            "€ " + str(saldo),
        )
    if saldo > 0:
        st.metric(
        "Ihr Guthaben",
        "€ " + str(st.session_state.user.get_saldo(conn)),
    )

    if saldo == 0:
        st.metric(
            "Ihr Saldo ist ausgeglichen",
            "€ 0",
        )


def widget_invoices(conn):
    invoices = st.session_state.user.get_invoices(conn)
    invoice_list = []
    for invoice in invoices:
        invoice_list.append(
            {
                "Rechnungsmonat": invoice.monat,
                "Betrag": invoice.gesamtbetrag,
                "Kaffeeanzahl": invoice.kaffee_anzahl,
                "bezahlt": invoice.bezahlt,
                "E-Mail-Versand am": invoice.email_versand,
                
            }
        )
    if len(invoice_list) == 0:
        return st.write("Keine Rechnungen gefunden.")
    return invoice_list


st.header("Meine Kaffeeübersicht")
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
    with st.container(border=True):
        st.subheader("Kaffeeanzahl im ausgewählten Monat")
        widget_kaffee_anzahl(datum, conn)
        st.subheader("Zahlungen im ausgewählten Monat")
        zahlungen = widget_payments(datum, conn)
        if zahlungen:
            st.dataframe(
                zahlungen,
                column_config={"Betrag": st.column_config.NumberColumn(format="€ %g"), "Datum": st.column_config.DatetimeColumn("Datum", format="DD.MM.YY")},
            )
    st.subheader("Saldo insgesamt")
    widget_saldo()
    st.divider()
    st.subheader("Meine Rechnungen")
    st.write(
        f"Rechnungen werden immer am Anfang eines Monats für den zurückliegenden Monat erstellt. Wenn Sie (z. B. wegen Urlaub) in einem Monat keinen Kaffee getrunken haben, wird auch keine Rechnung erstellt. Rechnungen gelten als bezahlt, sobald {st.secrets.admins.rechnung} den Rechnungseingang verbucht hat. Rechnungen mit einem negativen Betrag sind Guthaben. Solche Rechnungen sind immer automatisch als bezahlt markiert. Das Guthaben wird auf zukünftige Rechnungen angerechnet. Wenn Ihr Guthaben zu groß wird, können Sie sich das Guthaben bei {st.secrets.admins.rechnung} auszahlen lassen."
    )

    invoices = widget_invoices(conn)
    st.dataframe(
        invoices,
        column_config={
            "Betrag": st.column_config.NumberColumn("Rechnungsbetrag", format="€ %g"),
            "Rechnungsmonat": st.column_config.DatetimeColumn(
                "Rechnungsmonat", format="MMM YYYY"
            ),
            "bezahlt": st.column_config.DatetimeColumn("bezahlt am", format="DD.MM.YYYY"),
            "E-Mail-Versand am": st.column_config.DatetimeColumn(
                "E-Mail verschickt am", format="DD.MM.YYYY"
            ),
        },
    )
