"""Mietzahlungen der Mitglieder je Monat erfassen."""

import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.models import Mietzahlung, User
from db import get_connection
from helpers import get_first_days_of_last_six_months, monatsbereich

conn = get_connection()

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


def mietzahlung_buchen():
    """Callback der Aktionsspalte: verbucht die Miete des angeklickten Mitglieds.

    Streamlit legt den Klick als {"row": Zeilennummer, "label": Beschriftung}
    unter "klick_miete" ab. Der Callback läuft vor dem Seitenablauf, deshalb
    stammen Zeilenreihenfolge und Monat aus dem letzten Aufbau der Tabelle.
    """
    klick = st.session_state.get("klick_miete")
    if not klick:
        return
    ids = st.session_state.get("miete_mitglied_ids", [])
    if klick["row"] >= len(ids):
        return

    with conn.session as session:
        mitglied = session.get(User, ids[klick["row"]])
        if mitglied is None:
            st.error("Das Mitglied existiert nicht mehr.")
            return
        session.expunge(mitglied)

    # mietzahlung_eintragen öffnet seine eigene Session und meldet Erfolg
    # oder Fehler selbst.
    mitglied.mietzahlung_eintragen(conn, st.session_state["miete_monat"])


monate = get_first_days_of_last_six_months()
datum = st.selectbox("Abrechnungsmonat", monate, format_func=monatsname)

if datum:
    start, ende = monatsbereich(datum)
    with conn.session as session:
        bezahlt_ids = set(
            session.scalars(
                select(Mietzahlung.user_id).where(
                    Mietzahlung.monat >= start, Mietzahlung.monat < ende
                )
            )
        )
        mitglieder = list(
            session.scalars(select(User).where(User.mitglied == 1).order_by(User.name))
        )

    # offene zuerst, innerhalb der Gruppen nach Nachname
    mitglieder.sort(key=lambda m: (m.id in bezahlt_ids, m.name))
    offen = [m for m in mitglieder if m.id not in bezahlt_ids]

    st.subheader(f"Mietzahlungen {monatsname(datum)}")
    spalte1, spalte2, spalte3 = st.columns(3)
    spalte1.metric("Mitglieder", str(len(mitglieder)))
    spalte2.metric("Miete bezahlt", str(len(mitglieder) - len(offen)))
    spalte3.metric("noch offen", str(len(offen)))

    # Zeilenreihenfolge und Monat merken: der Klick-Callback bekommt nur eine
    # Zeilennummer und muss daraus Mitglied und Monat auflösen.
    st.session_state["miete_mitglied_ids"] = [m.id for m in mitglieder]
    st.session_state["miete_monat"] = datum

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Status": "✅ bezahlt" if m.id in bezahlt_ids else "❌ offen",
                    "Name": m.name,
                    "Vorname": m.vorname,
                    # Leere Zelle = kein Knopf: wer bezahlt hat, bekommt keinen.
                    "eintragen": None if m.id in bezahlt_ids else "Zahlung eintragen",
                }
                for m in mitglieder
            ],
            columns=["Status", "Name", "Vorname", "eintragen"],
        ),
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn(width="small"),
            "eintragen": st.column_config.ButtonColumn(
                "Mietzahlung",
                width="medium",
                type="primary",
                on_click=mietzahlung_buchen,
                key="klick_miete",
            ),
        },
    )
