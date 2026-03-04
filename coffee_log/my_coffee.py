import streamlit as st
import pandas as pd

from helpers import get_first_days_of_last_six_months
from api_client import get, post


def widget_kaffee_anzahl(datum):
    month_str = datum.strftime("%Y-%m")
    try:
        data = get("/coffee/month", params={"date": month_str})
        count = data.get("anzahl", 0)
        kaffee_liste = data.get("kaffee_liste") or []
    except Exception:
        st.error("Daten konnten nicht geladen werden.")
        return
    st.metric("getrunkene Tassen Kaffee", int(count))
    if kaffee_liste:
        df = pd.DataFrame([
            {"Datum": log["ts"][:10], "Anzahl": log["anzahl"]}
            for log in kaffee_liste
        ])
        if not df.empty:
            df_agg = df.groupby("Datum")["Anzahl"].sum().reset_index()
            st.dataframe(
                df_agg,
                column_config={"Datum": st.column_config.TextColumn("Datum")},
            )


def widget_payments(datum):
    month_str = datum.strftime("%Y-%m")
    try:
        payments = get("/payments", params={"month": month_str})
    except Exception:
        st.error("Zahlungen konnten nicht geladen werden.")
        return None
    if not payments:
        st.write("Sie haben in diesem Monat keine Einkäufe oder Auszahlungen abgerechnet.")
        return None
    return [
        {
            "Datum": p["ts"],
            "Typ": p["typ"],
            "Betrag": p["betrag"],
            "Betreff": p["betreff"],
        }
        for p in payments
    ]


def widget_saldo():
    try:
        data = get("/users/me/saldo")
        saldo = data.get("saldo", 0)
    except Exception:
        st.error("Saldo konnte nicht geladen werden.")
        return
    if saldo < 0:
        st.metric("offener Betrag", f"€ {saldo}")
    elif saldo > 0:
        st.metric("Ihr Guthaben", f"€ {saldo}")
    else:
        st.metric("Ihr Saldo ist ausgeglichen", "€ 0")


def widget_invoices():
    try:
        invoices = get("/users/me/invoices")
    except Exception:
        st.error("Rechnungen konnten nicht geladen werden.")
        return []
    return [
        {
            "Rechnungsmonat": inv["monat"],
            "Zahlbetrag": inv["gesamtbetrag"],
            "Kaffeekosten": inv["kaffee_preis"],
            "Kaffeeanzahl": inv["kaffee_anzahl"],
            "Einkäufe etc.": inv.get("payment_betrag"),
            "bezahlt": inv.get("bezahlt"),
            "E-Mail-Versand am": inv.get("email_versand"),
        }
        for inv in invoices
    ]


st.header("Meine Kaffeeübersicht")

uebersetzungen = {
    "January": "Januar", "February": "Februar", "March": "März", "April": "April",
    "May": "Mai", "June": "Juni", "July": "Juli", "August": "August",
    "September": "September", "October": "Oktober", "November": "November",
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
        widget_kaffee_anzahl(datum)
        st.subheader("Zahlungen im ausgewählten Monat")
        zahlungen = widget_payments(datum)
        if zahlungen:
            st.dataframe(
                zahlungen,
                column_config={
                    "Betrag": st.column_config.NumberColumn(format="€ %g"),
                    "Datum": st.column_config.TextColumn("Datum"),
                },
            )
        st.subheader("Mietanteil")
        try:
            month_str = datum.strftime("%Y-%m")
            status = get("/users/me/mietzahlung", params={"month": month_str})
            if status.get("paid"):
                st.write("✅ Ihre Mietzahlung wurde diesen Monat bereits verbucht.")
            else:
                st.write("❌ Ihre Mietzahlung ist noch nicht eingegangen.")
                if st.button("Mietzahlung eintragen", key=f"miet_{month_str}"):
                    try:
                        post("/users/me/mietzahlung", params={"month": month_str})
                        st.success("Mietzahlung erfolgreich eingetragen!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
        except Exception:
            st.write("❌ Ihre Mietzahlung ist noch nicht eingegangen.")

    st.subheader("Saldo insgesamt")
    widget_saldo()
    st.divider()
    st.subheader("Meine Rechnungen")
    try:
        admins = st.secrets.admins
        rechnung = admins.get("rechnung", "den Administrator")
    except Exception:
        rechnung = "den Administrator"
    st.write(
        f"Rechnungen werden immer am Anfang eines Monats für den zurückliegenden Monat erstellt. "
        f"Wenn Sie (z. B. wegen Urlaub) in einem Monat keinen Kaffee getrunken haben, wird auch keine Rechnung erstellt. "
        f"Rechnungen gelten als bezahlt, sobald {rechnung} den Rechnungseingang verbucht hat. "
        f"Rechnungen mit einem negativen Betrag sind Guthaben. Solche Rechnungen sind immer automatisch als bezahlt markiert. "
        f"Das Guthaben wird auf zukünftige Rechnungen angerechnet. "
        f"Wenn Ihr Guthaben zu groß wird, können Sie sich das Guthaben bei {rechnung} auszahlen lassen."
    )
    invoices = widget_invoices()
    if invoices:
        st.dataframe(
            invoices,
            column_config={
                "Zahlbetrag": st.column_config.NumberColumn("Rechnungsbetrag", format="€ %g"),
                "Rechnungsmonat": st.column_config.TextColumn("Rechnungsmonat"),
                "Einkäufe etc.": st.column_config.NumberColumn("Einkäufe etc.", format="€ %g"),
                "bezahlt": st.column_config.TextColumn("bezahlt am"),
                "E-Mail-Versand am": st.column_config.TextColumn("E-Mail verschickt am"),
            },
        )
    else:
        st.write("Keine Rechnungen gefunden.")
