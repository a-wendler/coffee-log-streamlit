import streamlit as st

from api_client import get

try:
    data = get("/account/overview")
except Exception as e:
    st.error(f"Kontoübersicht konnte nicht geladen werden: {e}")
    st.stop()

metrics = data.get("metrics", {})
offene_rechnungen = data.get("offene_rechnungen", [])
saldi = data.get("saldi", [])

st.title("Kontoübersicht")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Einzahlungen", "€ " + str(metrics.get("einzahlungen", 0)).replace(".", ","))
    st.metric("Auszahlungen", "€ " + str(metrics.get("auszahlungen", 0)).replace(".", ","))
    st.metric("Korrekturen", "€ " + str(metrics.get("korrekturen", 0)).replace(".", ","))
    st.metric(
        "Kassenstand",
        "€ " + str(metrics.get("kassenstand", 0)).replace(".", ","),
    )
    st.metric(
        "offene Rechnungen",
        "€ " + str(metrics.get("offene_rechnungen", 0)).replace(".", ","),
    )
    st.metric("Einkäufe", "€ " + str(metrics.get("einkaeufe", 0)).replace(".", ","))

with col2:
    st.metric("Kaffeeanzahl Mitglieder", str(metrics.get("mitgliederkaffees", 0)))
    st.metric("Kaffeeanzahl Gäste", str(metrics.get("gastkaffees", 0)))
    st.metric(
        "Kaffeeanzahl gesamt",
        str(metrics.get("kaffee_gesamt", 0)),
    )
    st.metric(
        "Summe der Guthaben",
        "€ " + str(metrics.get("summe_positiv", 0)).replace(".", ","),
    )
    st.metric(
        "Überschuss",
        "€ " + str(metrics.get("ueberschuss", 0)).replace(".", ","),
    )

with col3:
    st.metric(
        "Kaffeeumsatz Mitglieder",
        "€ " + str(metrics.get("mitgliedskosten", 0)).replace(".", ","),
    )
    st.metric(
        "Kaffeeumsatz Gäste",
        "€ " + str(metrics.get("gastkosten", 0)).replace(".", ","),
    )
    st.metric(
        "Kaffeeumsatz gesamt",
        "€ " + str(metrics.get("kaffeeumsatz_gesamt", 0)).replace(".", ","),
    )

st.subheader("offene Rechnungen")
if offene_rechnungen:
    st.dataframe(
        offene_rechnungen,
        column_config={
            "Betrag": st.column_config.NumberColumn(format="€ %g"),
            "Datum": st.column_config.TextColumn("Datum"),
        },
    )
else:
    st.write("Keine offenen Rechnungen.")

st.subheader("Saldi der Nutzenden")
if saldi:
    st.dataframe(
        saldi,
        column_config={"Saldo": st.column_config.NumberColumn(format="€ %g")},
    )

st.write(
    "Ein positiver Saldo bedeutet, dass die Person Guthaben hat. "
    "Negativer Saldo bedeutet, dass Rechnungen offen sind. "
    "Kaffees des laufenden Monats für den noch keine Abrechnung gemacht wurde sind im individuellen Saldo nicht enthalten."
)
