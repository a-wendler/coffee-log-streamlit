"""Kontoübersicht für Admins."""

from decimal import Decimal

import pandas as pd
import streamlit as st

from database.queries import NULL_BETRAG, get_offene_rechnungen, get_user_konten
from db import get_connection
from helpers import euro

conn = get_connection()

with conn.session as session:
    konten = get_user_konten(session)
    offene_rechnungen = get_offene_rechnungen(session)

einzahlungen = sum((k.einzahlungen for k in konten), NULL_BETRAG)
# Einkäufe sind Ausgaben der Kasse und werden deshalb negativ dargestellt.
einkaeufe = -sum((k.einkaeufe for k in konten), NULL_BETRAG)
auszahlungen = sum((k.auszahlungen for k in konten), NULL_BETRAG)
korrekturen = sum((k.korrekturen for k in konten), NULL_BETRAG)
# Abschlüsse beim Ausscheiden. Bewusst nicht im Kassenstand: Bei dieser
# Buchung fließt kein Geld, sie gleicht nur das Konto der Person aus.
abschluesse = sum((k.abschluesse for k in konten), NULL_BETRAG)

offene_rechnungen_summe = sum(
    (rechnung["Betrag"] for rechnung in offene_rechnungen), NULL_BETRAG
)

mitgliederkaffees = sum(k.kaffees for k in konten if k.mitglied)
gastkaffees = sum(k.kaffees for k in konten if not k.mitglied)

summe_positiv = sum((k.saldo for k in konten if k.saldo > 0), NULL_BETRAG)

# Nur freigeschaltete Konten. Die Kennzahlen oben bleiben bewusst über alle
# Konten gerechnet: eingezahltes Geld und getrunkener Kaffee ändern sich nicht
# dadurch, dass ein Konto noch nicht aktiviert ist.
saldi = [
    {
        "Name": k.name,
        "Vorname": k.vorname,
        "Mitglied": k.mitglied,
        "Saldo": k.saldo,
    }
    for k in konten
    if k.aktiv
]

mitgliedskosten = mitgliederkaffees * Decimal(st.secrets.KAFFEEPREIS_MITGLIED)
gastkosten = gastkaffees * Decimal(st.secrets.KAFFEEPREIS_GAST)

st.title("Kontoübersicht")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Einzahlungen", euro(einzahlungen))
    st.metric("Auszahlungen", euro(auszahlungen))
    st.metric("Korrekturen", euro(korrekturen))
    st.metric("Kassenstand", euro(einzahlungen + auszahlungen + korrekturen))
    st.metric(
        "Abschlüsse (Ausscheiden)",
        euro(abschluesse),
        help=(
            "Beim Ausscheiden ausgebuchte Beträge. Positiv: Schulden, welche "
            "die Gemeinschaft getragen hat. Negativ: Guthaben, das der Kasse "
            "geblieben ist. Kein Geldfluss, deshalb nicht im Kassenstand."
        ),
    )
    st.metric("offene Rechnungen", euro(offene_rechnungen_summe))
    st.metric("Einkäufe", euro(einkaeufe))

with col2:
    st.metric("Kaffeeanzahl Mitglieder", str(mitgliederkaffees))
    st.metric("Kaffeeanzahl Gäste", str(gastkaffees))
    st.metric("Kaffeeanzahl gesamt", str(mitgliederkaffees + gastkaffees))
    st.metric("Summe der Guthaben", euro(summe_positiv))
    st.metric("Überschuss", euro(mitgliedskosten + gastkosten + einkaeufe))

with col3:
    st.metric("Kaffeeumsatz Mitglieder", euro(mitgliedskosten))
    st.metric("Kaffeeumsatz Gäste", euro(gastkosten))
    st.metric("Kaffeeumsatz gesamt", euro(mitgliedskosten + gastkosten))

st.subheader("offene Rechnungen")
# Beträge über den Styler formatieren: NumberColumn kann nur einen Punkt als
# Dezimaltrennzeichen. Die Werte bleiben Zahlen und lassen sich weiter sortieren.
st.dataframe(
    pd.DataFrame(offene_rechnungen, columns=["Datum", "Betrag", "Nutzer"]).style.format(
        {"Betrag": euro}, na_rep=""
    ),
    hide_index=True,
    column_config={"Datum": st.column_config.DatetimeColumn(format="DD.MM.YY")},
)

st.subheader("Saldi der Nutzenden")
st.dataframe(
    pd.DataFrame(saldi, columns=["Name", "Vorname", "Mitglied", "Saldo"]).style.format(
        {"Saldo": euro}, na_rep=""
    ),
    hide_index=True,
)

st.write(
    "Ein positiver Saldo bedeutet, dass die Person Guthaben hat. Negativer Saldo bedeutet, dass Rechnungen offen sind. Kaffees des laufenden Monats für den noch keine Abrechnung gemacht wurde sind im individuellen Saldo nicht enthalten."
)
