"""
Module for editing payment data.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import select
from loguru import logger
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP
import calendar
import hashlib
import math

from database.models import PAYMENT_TYPEN, PAYMENT_TYPEN_MANUELL, User, Payment
from db import get_connection

def new_payment():
    """Add new payment."""
    with conn.session as session:
        try:
            payment = Payment(
                user_id=st.session_state.user_selection,
                betreff=st.session_state.betreff,
                typ=st.session_state.typ,
                betrag=st.session_state.betrag,
                # st.date_input liefert ein date, die Spalte ist DATETIME
                ts=datetime.combine(st.session_state.ts, time.min),
            )
            if payment.typ == "Auszahlung":
                payment.betrag = -payment.betrag

            payment.save(session)
            st.success("Zahlung wurde hinzugefügt!")
        except Exception as e:
            session.rollback()
            logger.error(f"Beim Hinzufügen der Zahlung ist ein Fehler aufgetreten: {e}")
            st.error(f"Beim Hinzufügen der Zahlung ist ein Fehler aufgetreten: {e}")
        


# Die Tabelle zeigt deutsche Spaltentitel, die Datenbank hat andere Feldnamen.
# Ohne diese Zuordnung lief setattr(payment, "Betrag", …) ins Leere und jede
# Änderung wurde stillschweigend verworfen.
SPALTE_ZU_FELD = {
    "Betrag": "betrag",
    "Betreff": "betreff",
    "Typ": "typ",
    "Datum": "ts",
}


def feldwert(feld, wert):
    """Wandelt einen Wert aus der Tabelle in das Format der Datenbank."""
    if feld == "betreff":
        return wert or None
    if wert is None or wert == "":
        raise ValueError(f"Das Feld „{feld}“ darf nicht leer sein.")
    if feld == "betrag":
        return Decimal(str(wert)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if feld == "ts":
        # ts ist eine DATETIME-Spalte; das Datum wird zu Mitternacht gespeichert.
        return datetime.combine(wert, time.min) if isinstance(wert, date) else wert
    return wert


def edit_payment_data(editor_schluessel):
    """Speichert die im Editor geänderten Zeilen."""
    aenderungen = st.session_state[editor_schluessel].get("edited_rows", {})
    if not aenderungen:
        st.info("Es gab keine Änderungen zum Speichern.")
        return

    with conn.session as session:
        try:
            for zeile, felder in aenderungen.items():
                payment_id = int(edited_df.iloc[int(zeile)]["ID"])
                payment = session.scalar(
                    select(Payment).where(Payment.id == payment_id)
                )
                if payment is None:
                    raise ValueError(f"Zahlung {payment_id} existiert nicht mehr.")
                for spalte, wert in felder.items():
                    feld = SPALTE_ZU_FELD.get(spalte)
                    if feld is None:
                        continue  # ID und Einzahler sind nicht änderbar
                    setattr(payment, feld, feldwert(feld, wert))
            session.commit()
            st.success(f"{len(aenderungen)} Zahlung(en) gespeichert.")
        except Exception as e:
            session.rollback()
            logger.error(f"Zahlungen konnten nicht gespeichert werden: {e}")
            st.error(f"Die Änderungen konnten nicht gespeichert werden: {e}")

def reset_form(keys):
    for k in keys:
        st.session_state.pop(k, None)
    st.rerun()

# Streamlit app layout
# menu_with_redirect()
# st.write(st.session_state)
conn = get_connection()
st.subheader("Zahlung hinzufügen")

# Namen der Mitglieder einmal laden. Vorher lief die format_func der selectbox
# pro Eintrag der Auswahlliste in eine eigene Query.
with conn.session as session:
    mitglieder = dict(
        session.execute(
            select(User.id, User.name).filter(User.mitglied == 1)
        ).all()
    )

with st.form(key="payment_form", clear_on_submit=True):
    user = st.selectbox(
        "Nutzer",
        list(mitglieder),
        format_func=lambda user_id: mitglieder[user_id],
        key="user_selection",
    )
    betreff = st.text_input("Betreff", key="betreff")
    typ = st.selectbox(
        "Typ",
        PAYMENT_TYPEN_MANUELL,
        key="typ",
    )
    betrag = st.number_input("Betrag", key="betrag")
    ts = st.date_input("Datum", key="ts", format="DD.MM.YYYY")
    submit = st.form_submit_button("Zahlung hinzufügen", on_click=new_payment)

st.subheader("Zahlungen bearbeiten")

# Der Name kommt über einen Join direkt mit. Vorher wurde er über
# payment.user nachgeladen – eine Query je Zahlung.
with conn.session as session:
    zahlungen = session.execute(
        select(
            Payment.id,
            User.name,
            Payment.betrag,
            Payment.betreff,
            Payment.typ,
            Payment.ts,
        )
        .join(Payment.user)
        # neueste zuerst: die zuletzt erfassten Zahlungen sind die,
        # die man üblicherweise noch einmal ansehen oder korrigieren will
        .order_by(Payment.id.desc())
    ).all()

df = pd.DataFrame.from_records(
    zahlungen,
    columns=["ID", "Einzahler", "Betrag", "Betreff", "Typ", "Datum"],
)
# ts ist eine DATETIME-Spalte; fuer Filter und Editor reicht das Datum.
df["Datum"] = df["Datum"].map(lambda w: w.date() if w is not None else None)

df_filter = df.copy()

with st.expander('Tabelle filtern'):
    with st.form("data_editor_filter"):
        left, right = st.columns(2)
        today = date.today()

        filter_einzahler = left.multiselect(
            "Einzahler",
            df["Einzahler"].sort_values().unique().tolist(),
            key="f_einzahler"
        )

        filter_typ = right.multiselect(
            "Typ",
            PAYMENT_TYPEN,
            key="f_typ"
        )

        # default to current month range
        start_default = today.replace(day=1)
        end_default = today.replace(day=calendar.monthrange(today.year, today.month)[1])

        filter_datum = left.date_input(
            "Datum",
            value=(start_default, end_default),
            format="DD/MM/YYYY",
            key="f_datum"
        )

        submitted = left.form_submit_button("Filtern")
        reset = left.form_submit_button("Reset", on_click=reset_form, kwargs={"keys": ["f_einzahler","f_typ","f_datum"]}, type='secondary')

        if submitted:
            mask = pd.Series(True, index=df.index)

            # Only apply if selections exist
            if filter_einzahler:
                mask &= df["Einzahler"].isin(filter_einzahler)

            if filter_typ:
                mask &= df["Typ"].isin(filter_typ)

            # st.date_input liefert je nach Auswahl ein Datum oder ein Tupel
            if isinstance(filter_datum, tuple) and len(filter_datum) == 2:
                start_date, end_date = filter_datum
                mask &= (df["Datum"] >= start_date) & (df["Datum"] <= end_date)

            df_filter = df.loc[mask]

        if reset:
            df_filter = df.copy()

SEITENGROESSE = 25

# Die Tabelle wird oberhalb der Blätterleiste ausgegeben, obwohl die Seitenzahl
# vorher feststehen muss.
tabellen_bereich = st.container()

anzahl_seiten = max(1, math.ceil(len(df_filter) / SEITENGROESSE))
seite = st.pagination(anzahl_seiten, key="zahlungen_seite")
von = (seite - 1) * SEITENGROESSE
seiten_df = df_filter.iloc[von : von + SEITENGROESSE]

if len(df_filter):
    st.caption(
        f"Zahlungen {von + 1}–{von + len(seiten_df)} von {len(df_filter)}"
    )
else:
    st.caption("Keine Zahlungen für diese Auswahl.")

# Der Schlüssel des Editors hängt an den angezeigten Zeilen. Beim Blättern oder
# Filtern entsteht dadurch ein neuer Editor mit leerem Zustand -- sonst könnten
# die gemerkten Zeilennummern einer anderen Seite zugeordnet und damit die
# falsche Zahlung geändert werden.
editor_schluessel = "data_editor_" + hashlib.md5(
    ",".join(str(i) for i in seiten_df["ID"]).encode()
).hexdigest()[:10]

with tabellen_bereich, st.form(key="edit_payment_data"):
    edited_df = st.data_editor(
        seiten_df,
        key=editor_schluessel,
        hide_index=True,
        # Vorher standen hier "id" und "name" – Spalten, die es nicht gibt.
        # Damit waren ID und Einzahler bearbeitbar, ohne dass es Wirkung hatte.
        disabled=["ID", "Einzahler"],
        column_config={
            # Die Spalte bleibt editierbar, deshalb kein Styler (den ignoriert
            # der data_editor). "euro" formatiert nach der Spracheinstellung des
            # Browsers, auf Deutsch also "3,00 €".
            "Betrag": st.column_config.NumberColumn("Betrag", format="euro"),
            # Alle Arten, auch "Abschluss": Eine Zeile mit einem Wert, der
            # nicht in den Optionen steht, lässt sich im Editor nicht anzeigen.
            "Typ": st.column_config.SelectboxColumn("Typ", options=PAYMENT_TYPEN),
            "Datum": st.column_config.DateColumn("Datum", format="DD.MM.YYYY"),
        },
    )
    st.form_submit_button(
        "Änderungen speichern",
        on_click=edit_payment_data,
        args=(editor_schluessel,),
    )
