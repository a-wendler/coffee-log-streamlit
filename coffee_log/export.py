"""Datenexport als Excel-Mappe."""

from datetime import datetime
from functools import partial

import streamlit as st

from database.queries import get_exportdaten, get_exportumfang
from db import get_connection
from excel_export import dateiname, export_als_excel

conn = get_connection()


def mappe_erzeugen(conn) -> bytes:
    """Baut die Excel-Mappe - erst beim Klick auf den Knopf.

    st.download_button ruft diese Funktion nur auf, wenn wirklich jemand
    herunterlädt, und zwar in einem eigenen Thread. Der Export liest alle
    Kaffees und alle Zahlungen; beim Aufbau der Seite soll das nicht jedes Mal
    passieren, nur weil der Knopf dasteht.
    """
    with conn.session as session:
        daten = get_exportdaten(session)
    return export_als_excel(daten)


st.title("Datenexport")
st.write(
    "Alle Daten der App in einer Excel-Mappe mit drei Blättern. Die Namen "
    "stehen in den Zeilen, es müssen also keine Nutzernummern nachgeschlagen "
    "werden."
)

with conn.session as session:
    umfang = get_exportumfang(session)

spalte1, spalte2, spalte3 = st.columns(3)
spalte1.metric("Kaffees", str(umfang["kaffees"]), help="Blatt „Kaffees“: jeder einzelne Eintrag")
spalte2.metric("Zahlungen", str(umfang["zahlungen"]), help="Blatt „Zahlungen“: jede Buchung")
spalte3.metric("Konten", str(umfang["konten"]), help="Blatt „Kontoübersicht“: ein Konto je Zeile")

st.markdown(
    "- **Kaffees** – Datum, Name, Anzahl und ob der Eintrag schon in einer "
    "Rechnung steht\n"
    "- **Zahlungen** – Datum, Name, Art, Betrag, Betreff und die "
    "Rechnungsnummer, sofern die Buchung zu einer Rechnung gehört\n"
    "- **Kontoübersicht** – je Konto der Saldo, Anzahl und Summe der offenen "
    "Rechnungen sowie die Kaffees, für die noch keine Rechnung erstellt wurde"
)

st.download_button(
    "Excel-Mappe herunterladen",
    data=partial(mappe_erzeugen, conn),
    file_name=dateiname(datetime.now()),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
    icon=":material/download:",
)

st.caption(
    "Die Mappe wird erst beim Klick gebaut; bei vielen Einträgen dauert das "
    "einen Moment. Ein negativer Saldo bedeutet, dass noch etwas offen ist, "
    "ein positiver ist Guthaben. Kaffees, für die noch keine Rechnung "
    "erstellt wurde, stecken nicht im Saldo - sie stehen deshalb in einer "
    "eigenen Spalte."
)
