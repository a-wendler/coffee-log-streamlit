"""Monthly billing (Abrechnung) - uses API."""

import streamlit as st

from helpers import get_first_days_of_last_six_months
from api_client import get, post


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
    month_str = datum.strftime("%Y-%m")
    try:
        data = get("/invoices", params={"month": month_str})
    except Exception as e:
        st.error(f"Daten konnten nicht geladen werden: {e}")
        st.stop()

    booked = data.get("booked", False)
    invoices = data.get("invoices", [])
    summary = data.get("summary")

    if booked:
        st.subheader("Gebuchte Rechnungen")
        for inv in invoices:
            bezahlt_icon = "✅" if inv.get("bezahlt") else "❌"
            email_icon = "📧" if inv.get("email_versand") else ""
            with st.expander(label=f"{bezahlt_icon} {email_icon} {inv['user_name']}"):
                st.write("Zahlbetrag:", inv["gesamtbetrag"])
                st.write("Kaffeeanzahl:", inv["kaffee_anzahl"])
                st.write("Kaffeekosten:", inv["kaffee_preis"])
                st.write("Einkäufe, Auszahlungen etc.:", inv.get("payment_betrag"))
                st.write("Erstellt:", inv.get("ts"))
                st.write("Bezahlt:", inv.get("bezahlt"))
                st.write("Zahlungen:")
                for p in inv.get("payments", []):
                    st.write(p.get("betrag"), p.get("betreff"), p.get("ts"))
                if not inv.get("bezahlt"):
                    if st.button("Rechnung als bezahlt markieren", key=f"paid_{inv['id']}"):
                        try:
                            post(f"/invoices/{inv['id']}/mark-paid")
                            st.success("Rechnung als bezahlt markiert")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
                if st.button("Rechnung senden", key=f"send_{inv['id']}"):
                    try:
                        post(f"/invoices/{inv['id']}/send-email")
                        st.success("Rechnung versendet!")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
                if inv.get("gesamtbetrag", 0) <= 0:
                    st.write("Keine Zahlung fällig. Kaffeekosten wurden mit Guthaben verrechnet.")
    else:
        st.write("Es wurden noch keine Rechnungen für diesen Monat gebucht.")
        if summary:
            st.subheader("Gesamtabrechnung")
            s = summary
            st.write("Mitgliederkaffees:", s.get("mitgliederkaffees", 0))
            st.write("Gastkaffees:", s.get("gastkaffees", 0))
            st.write("Gesamtkaffees:", s.get("mitgliederkaffees", 0) + s.get("gastkaffees", 0))
            st.write("Monatseinnahmen: €", s.get("monatseinnahmen", 0))
            st.write("Verbrauchskosten: €", s.get("zahlungssumme", 0))
            st.write("Überschuss: €", s.get("ueberschuss", 0))
            st.subheader("Zahlungen")
            if s.get("payment_list"):
                st.dataframe(
                    s["payment_list"],
                    column_config={
                        "Betrag": st.column_config.NumberColumn(format="€ %.2f"),
                        "Datum": st.column_config.TextColumn("Datum"),
                    },
                )
        st.subheader("Einzelabrechnungen")
        if invoices:
            df_data = [
                {
                    "Name": inv.get("user_name", ""),
                    "Zahlbetrag": inv.get("gesamtbetrag", 0),
                    "Kaffeeanzahl": inv.get("kaffee_anzahl", 0),
                    "Kaffeekosten": inv.get("kaffee_preis", 0),
                    "Einkäufe": inv.get("payment_betrag"),
                    "Guthaben alt": inv.get("guthaben_alt", 0),
                }
                for inv in invoices
            ]
            st.dataframe(
                df_data,
                column_config={
                    "Zahlbetrag": st.column_config.NumberColumn(format="€ %g"),
                    "Kaffeekosten": st.column_config.NumberColumn(format="€ %g"),
                    "Einkäufe": st.column_config.NumberColumn(format="€ %g"),
                    "Guthaben alt": st.column_config.NumberColumn(format="€ %g"),
                },
            )
            if st.button(f"Monatsabrechnung {uebersetzungen[datum.strftime('%B')]} erstellen"):
                st.session_state["show_confirm_abrechnung"] = True
        if st.session_state.get("show_confirm_abrechnung"):
            st.warning("Wollen Sie die Monatsabrechnung wirklich erstellen und die Rechnungen einbuchen?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Ja, buchen"):
                    try:
                        post("/invoices/month", params={"month": month_str})
                        st.success("Buchung erfolgreich")
                        st.session_state.pop("show_confirm_abrechnung", None)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with col2:
                if st.button("Nein, abbrechen"):
                    st.session_state.pop("show_confirm_abrechnung", None)
                    st.rerun()
