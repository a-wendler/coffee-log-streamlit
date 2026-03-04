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
        mitglieder_liste = get("/mietzahlungen", params={"month": month_str})
    except Exception as e:
        st.error(f"Mietzahlungen konnten nicht geladen werden: {e}")
        mitglieder_liste = []

    for m in mitglieder_liste:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(m["name"])
            with col2:
                if m.get("paid"):
                    st.write("✅")
                else:
                    if st.button(
                        "Zahlung eintragen",
                        key=f"miet_{month_str}_{m['user_id']}",
                    ):
                        try:
                            post(
                                "/mietzahlungen",
                                json={"user_id": m["user_id"], "month": month_str},
                            )
                            st.success("Mietzahlung eingetragen!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
