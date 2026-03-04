"""Debug page for balance/invoice verification - uses API."""

import streamlit as st

from api_client import get

st.subheader("Guthaben Test (Debug)")

try:
    data = get("/account/overview")
    saldi = data.get("saldi", [])
    offene = data.get("offene_rechnungen", [])
    st.write("Saldi der Nutzenden:")
    st.dataframe(saldi, column_config={"Saldo": st.column_config.NumberColumn(format="€ %g")})
    st.write("Offene Rechnungen:")
    st.dataframe(offene)
except Exception as e:
    st.error(f"Fehler: {e}")
