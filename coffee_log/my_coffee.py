"""Persönliche Kaffeeübersicht."""

from decimal import Decimal

import pandas as pd
import streamlit as st

from database.queries import (
    get_monatslogs,
    get_monatspayments,
    get_rechnungen,
    get_rechnungsdaten,
    get_saldo,
    hat_mietzahlung,
)
from db import get_connection
from helpers import euro, get_first_days_of_last_six_months, monatsname
from rechnung_pdf import dateiname, rechnung_als_pdf

def widget_kaffee_anzahl(logs):
    """Tassenzahl des Monats und Aufstellung nach Tagen."""
    st.metric("getrunkene Tassen Kaffee", sum(log.anzahl for log in logs))
    if not logs:
        st.write("Sie haben in diesem Monat keinen Kaffee eingetragen.")
        return
    df = pd.DataFrame(
        [{"Datum": log.ts.date(), "Anzahl": log.anzahl} for log in logs]
    )
    st.dataframe(
        df.groupby("Datum")["Anzahl"].sum().reset_index(),
        column_config={
            "Datum": st.column_config.DatetimeColumn("Datum", format="DD.MM.YY")
        },
    )


def widget_payments(payments):
    """Einkäufe und Auszahlungen des Monats."""
    if not payments:
        st.write(
            "Sie haben in diesem Monat keine Einkäufe oder Auszahlungen abgerechnet."
        )
        return
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Datum": payment.ts,
                    "Typ": payment.typ,
                    "Betrag": payment.betrag,
                    "Betreff": payment.betreff,
                }
                for payment in payments
            ],
            columns=["Datum", "Typ", "Betrag", "Betreff"],
        ).style.format({"Betrag": euro}, na_rep=""),
        hide_index=True,
        column_config={
            "Datum": st.column_config.DatetimeColumn("Datum", format="DD.MM.YY"),
        },
    )


def widget_zahlungsstatus(saldo, offene_rechnungen):
    """Die eine Frage, die jede Person hat: Muss ich etwas bezahlen?

    Maßgeblich ist die Summe der offenen Rechnungen, nicht der Saldo: Nur eine
    Rechnung ist eine konkrete Zahlungsaufforderung. Ein negativer Saldo ohne
    offene Rechnung (etwa nach einer Korrektur) wird deshalb getrennt gemeldet
    - er wird mit der nächsten Rechnung verrechnet.
    """
    faellig = sum((r.gesamtbetrag for r in offene_rechnungen), Decimal("0.00"))

    if faellig > 0:
        anzahl = len(offene_rechnungen)
        monate = ", ".join(monatsname(r.monat) for r in offene_rechnungen)
        st.error(
            f"### ❗ Sie müssen noch {euro(faellig)} bezahlen\n\n"
            + (
                f"Offen ist die Rechnung für {monate}."
                if anzahl == 1
                else f"Offen sind {anzahl} Rechnungen: {monate}."
            )
        )
        st.info(f"**So können Sie zahlen**\n\n{st.secrets.ZAHLUNGSOPTIONEN}")
        return

    if saldo < 0:
        st.warning(
            f"### Nichts zu bezahlen\n\nIhr Saldo steht bei {euro(saldo)}. "
            "Dieser Betrag wird mit Ihrer nächsten Rechnung verrechnet."
        )
        return

    if saldo > 0:
        st.success(
            f"### ✅ Sie haben nichts offen\n\nSie haben sogar ein Guthaben "
            f"von {euro(saldo)}, das auf Ihre nächsten Rechnungen angerechnet "
            "wird."
        )
        return

    st.success("### ✅ Sie haben nichts offen\n\nIhr Konto ist ausgeglichen.")


def widget_saldo(saldo):
    """Guthaben bzw. offener Betrag als Zahl."""
    if saldo < 0:
        st.metric("offener Betrag", euro(saldo))
    elif saldo > 0:
        st.metric("Ihr Guthaben", euro(saldo))
    else:
        st.metric("Ihr Saldo ist ausgeglichen", euro(0))


# Breiten so gewählt, dass "Kaffeekosten" in eine Zeile passt.
SPALTEN = [2.0, 0.9, 1.6, 1.5, 1.5, 1.2]


def _rechnungszeile(felder, fett=False):
    """Eine Zeile der Rechnungsliste; die letzte Spalte bleibt für den Knopf."""
    spalten = st.columns(SPALTEN, vertical_alignment="center")
    for spalte, text in zip(spalten, felder):
        spalte.markdown(f"**{text}**" if fett else text)
    return spalten[-1]


def widget_invoices(invoices, pdf_daten, zahlungsoptionen):
    """Rechnungsliste mit einem Herunterladen-Knopf je Zeile.

    Bewusst keine st.dataframe-Tabelle: Aus einer Tabellenzelle heraus lässt
    sich kein Download auslösen, ein ButtonColumn kann nur einen Callback
    aufrufen. Mit eigenen Zeilen genügt ein Klick.
    """
    if not invoices:
        st.write("Für dieses Jahr gibt es keine Rechnungen.")
        return

    _rechnungszeile(
        ["Monat", "Tassen", "Kaffeekosten", "Zahlbetrag", "Status", ""], fett=True
    )
    for invoice in invoices:
        if invoice.bezahlt:
            status = "✅ bezahlt"
        elif invoice.gesamtbetrag > 0:
            status = "❗ offen"
        else:
            status = "✅ ausgeglichen"

        knopf = _rechnungszeile(
            [
                monatsname(invoice.monat),
                str(invoice.kaffee_anzahl),
                euro(invoice.kaffee_preis),
                euro(invoice.gesamtbetrag),
                status,
                "",
            ]
        )

        daten = pdf_daten.get(invoice.id)
        if daten is None:
            continue
        knopf.download_button(
            "PDF",
            data=rechnung_als_pdf(
                daten,
                zahlungsoptionen,
                st.secrets.admins["rechnung"],
                st.secrets.admins["technik"],
            ),
            file_name=dateiname(daten),
            mime="application/pdf",
            key=f"pdf_{invoice.id}",
            width="stretch",
        )


def widget_rechnungen(invoices, conn):
    """Jahresauswahl und Rechnungsliste."""
    if not invoices:
        st.write("Keine Rechnungen gefunden.")
        return

    jahre = sorted({invoice.monat.year for invoice in invoices}, reverse=True)
    jahr = st.selectbox("Jahr", jahre, key="rechnungsjahr")

    # neueste zuerst: die aktuelle Rechnung ist die, nach der man sucht
    des_jahres = sorted(
        (invoice for invoice in invoices if invoice.monat.year == jahr),
        key=lambda invoice: invoice.monat,
        reverse=True,
    )

    # Die PDF-Daten nur für das gewählte Jahr laden, in einer Session.
    with conn.session as session:
        pdf_daten = {
            invoice.id: get_rechnungsdaten(session, invoice.id)
            for invoice in des_jahres
        }

    widget_invoices(des_jahres, pdf_daten, st.secrets.ZAHLUNGSOPTIONEN)


st.header("Meine Kaffeeübersicht")
conn = get_connection()

# Nach dem Eintragen auf der Startseite landet man hier. Die Bestätigung
# kommt deshalb erst auf dieser Seite an.
gebucht = st.session_state.pop("kaffee_gebucht", None)
if gebucht:
    st.success(
        f"{gebucht} Kaffee eingetragen!"
        if gebucht == 1
        else f"{gebucht} Kaffees eingetragen!"
    )

user_id = st.session_state.user.id

# Der Zahlungsstand gilt für das ganze Konto und hängt nicht am Monat. Er
# steht deshalb noch vor der Monatsauswahl – es ist die Frage, mit der die
# meisten diese Seite aufrufen.
with conn.session as session:
    saldo = get_saldo(session, user_id)
    invoices = get_rechnungen(session, user_id)

offene_rechnungen = [invoice for invoice in invoices if invoice.bezahlt is None]
widget_zahlungsstatus(saldo, offene_rechnungen)

st.divider()
monate = get_first_days_of_last_six_months()
datum = st.selectbox("Abrechnungsmonat", monate, format_func=monatsname)

if datum:
    # Die Monatsdaten in einer einzigen Session laden, danach nur noch
    # darstellen – so löst das Rendern keine weiteren Queries mehr aus.
    with conn.session as session:
        logs = get_monatslogs(session, user_id, datum)
        payments = get_monatspayments(session, user_id, datum)
        miete_bezahlt = hat_mietzahlung(session, user_id, datum)

    with st.container(border=True):
        st.subheader("Kaffeeanzahl im ausgewählten Monat")
        widget_kaffee_anzahl(logs)
        st.subheader("Zahlungen im ausgewählten Monat")
        widget_payments(payments)
        st.subheader("Mietanteil")
        if miete_bezahlt:
            st.write("✅ Ihre Mietzahlung wurde diesen Monat bereits verbucht.")
        else:
            st.write("❌ Ihre Mietzahlung ist noch nicht eingegangen.")

    st.subheader("Saldo insgesamt")
    widget_saldo(saldo)
    st.divider()
    st.subheader("Meine Rechnungen")
    st.write(
        f"Rechnungen werden immer am Anfang eines Monats für den zurückliegenden Monat erstellt. Wenn Sie (z. B. wegen Urlaub) in einem Monat keinen Kaffee getrunken haben, wird auch keine Rechnung erstellt. Rechnungen gelten als bezahlt, sobald {st.secrets.admins.rechnung} den Rechnungseingang verbucht hat. Rechnungen mit einem negativen Betrag sind Guthaben. Solche Rechnungen sind immer automatisch als bezahlt markiert. Das Guthaben wird auf zukünftige Rechnungen angerechnet. Wenn Ihr Guthaben zu groß wird, können Sie sich das Guthaben bei {st.secrets.admins.rechnung} auszahlen lassen."
    )
    widget_rechnungen(invoices, conn)
