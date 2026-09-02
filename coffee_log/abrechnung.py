import pandas as pd
import streamlit as st
from contextlib import contextmanager
from loguru import logger
from sqlalchemy import select, or_
from sqlalchemy.orm import contains_eager, selectinload
from database.models import Log, User, Payment, Invoice
from database.queries import get_saldi
from db import get_connection
from helpers import euro, get_first_days_of_last_six_months, monatsbereich
from decimal import Decimal
from typing import List, Union
from datetime import datetime


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    try:
        with conn.session as session:
            yield session
            # session.commit()
    except Exception as e:
        logger.error(f"Database error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def quantize_decimal(value: Union[Decimal, int, float, str]) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
    return Decimal(value).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


def monatsliste(datum: datetime, saldi: dict) -> List[Invoice]:

    invoices = []
    for user in st.session_state[datum]["users"]:

        kaffee_anzahl = sum(log.anzahl for log in user.logs)
        if kaffee_anzahl == 0:
            continue
        payment_betrag = sum(payment.betrag for payment in user.payments)

        kaffee_preis = (
            kaffee_anzahl * quantize_decimal(st.secrets.KAFFEEPREIS_MITGLIED)
            if user.mitglied
            else kaffee_anzahl * quantize_decimal(st.secrets.KAFFEEPREIS_GAST)
        )
        saldo = saldi.get(user.id, quantize_decimal("0"))
        bezahlt = None
        if saldo > 0:  # Nutzer hat noch Guthaben
            if saldo - kaffee_preis < 0:  # Nutzer hat nicht genug Guthaben
                gesamtbetrag = (
                    kaffee_preis - saldo
                )  # Guthaben wird verrechnet und Restbetrag ist fällig
            if saldo - kaffee_preis >= 0:  # Nutzer hat genug Guthaben
                gesamtbetrag = quantize_decimal("0")  # es ist keine Zahlung fällig
                bezahlt = datetime.now()
        if saldo <= 0:  # Nutzer hat kein Guthaben
            gesamtbetrag = quantize_decimal(kaffee_preis)

        invoices.append(
            Invoice(
                kaffee_anzahl=kaffee_anzahl,
                kaffee_preis=kaffee_preis,
                payment_betrag=payment_betrag,
                gesamtbetrag=gesamtbetrag,
                monat=datum,
                payments=user.payments,
                user_id=user.id,
                user=user,
                ts=datetime.now(),
                bezahlt=bezahlt,
            )
        )
    st.session_state[datum]["invoices"] = invoices


@st.dialog("Monatsabrechnung erstellen?")
def confirm_monatsabrechnung():
    st.write(
        "Wollen Sie die Monatsabrechnung wirklich erstellen und die Rechnungen einbuchen?"
    )
    if st.button("Ja"):
        monatsbuchung(datum)
        st.rerun()
    if st.button("Nein"):
        st.rerun()


def monatsbuchung(datum):
    with get_db_connection() as session:
        try:
            for invoice in st.session_state[datum]["invoices"]:
                invoice.monat = datum
                invoice.ts = datetime.now()
                session.add(invoice)
            session.commit()
            st.success("Buchung erfolgreich")
        except Exception as e:
            st.error("Fehler bei der Buchung")
            logger.error(f"Fehler bei der Buchung: {e}")
            session.rollback()


def _rechnung_aus_klick(schluessel: str):
    """Ermittelt die angeklickte Rechnungs-ID aus dem Klick in der Tabelle.

    Streamlit legt den Klick als {"row": Zeilennummer, "label": Beschriftung}
    unter dem angegebenen Schlüssel ab. Der Callback läuft vor dem Seitenablauf,
    deshalb wird die Zeilenreihenfolge aus dem letzten Aufbau der Tabelle
    verwendet, die dort in st.session_state hinterlegt wurde.
    """
    klick = st.session_state.get(schluessel)
    if not klick:
        return None
    ids = st.session_state.get("rechnungs_ids", [])
    zeile = klick["row"]
    if zeile >= len(ids):
        return None
    return ids[zeile]


def rechnung_bezahlt_markieren():
    """Verbucht den Zahlungseingang für die angeklickte Rechnung."""
    rechnungs_id = _rechnung_aus_klick("klick_bezahlt")
    if rechnungs_id is None:
        return
    # Eigene Session: die Session des Seitenaufbaus ist zum Zeitpunkt des
    # Callbacks längst geschlossen.
    with conn.session as session:
        rechnung = session.get(Invoice, rechnungs_id)
        if rechnung is None:
            st.error("Die Rechnung existiert nicht mehr.")
            return
        rechnung.mark_as_paid(session)


def rechnung_details_merken():
    """Merkt die Rechnung vor; Dialoge lassen sich nicht im Callback öffnen."""
    rechnungs_id = _rechnung_aus_klick("klick_details")
    if rechnungs_id is not None:
        st.session_state["details_rechnung"] = rechnungs_id


@st.dialog("Rechnungsdetails")
def zeige_rechnungsdetails(rechnungs_id: int):
    """Einzelheiten einer Rechnung inklusive der zugehörigen Zahlungen."""
    with conn.session as session:
        rechnung = session.scalar(
            select(Invoice)
            .options(selectinload(Invoice.payments), contains_eager(Invoice.user))
            .join(Invoice.user)
            .where(Invoice.id == rechnungs_id)
        )
        if rechnung is None:
            st.error("Die Rechnung existiert nicht mehr.")
            return

        st.write(f"**{rechnung.user.vorname} {rechnung.user.name}**")
        links, rechts = st.columns(2)
        links.metric("Zahlbetrag", euro(rechnung.gesamtbetrag))
        rechts.metric("Kaffeeanzahl", str(rechnung.kaffee_anzahl))
        links.metric("Kaffeekosten", euro(rechnung.kaffee_preis))
        rechts.metric("Einkäufe, Auszahlungen etc.", euro(rechnung.payment_betrag or 0))

        st.write("Erstellt:", rechnung.ts.strftime("%d.%m.%Y %H:%M"))
        st.write(
            "Bezahlt:",
            rechnung.bezahlt.strftime("%d.%m.%Y %H:%M") if rechnung.bezahlt else "–",
        )

        st.subheader("Verbuchte Zahlungen")
        if rechnung.payments:
            st.dataframe(
                [
                    {
                        "Datum": zahlung.ts,
                        "Betrag": zahlung.betrag,
                        "Betreff": zahlung.betreff,
                    }
                    for zahlung in rechnung.payments
                ],
                hide_index=True,
                column_config={
                    "Datum": st.column_config.DatetimeColumn(format="DD.MM.YYYY"),
                    "Betrag": st.column_config.NumberColumn(format="€ %.2f"),
                },
            )
        else:
            st.write("Zu dieser Rechnung wurde noch keine Zahlung verbucht.")

        if rechnung.gesamtbetrag <= 0:
            st.info(
                "Keine Zahlung fällig. Die Kaffeekosten wurden mit dem Guthaben verrechnet."
            )


# Main Application

conn = get_connection()

uebersetzungen = {
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
monate = get_first_days_of_last_six_months()
datum = st.selectbox(
    "Abrechnungsmonat",
    monate,
    format_func=lambda x: uebersetzungen[x.strftime("%B")] + " " + x.strftime("%Y"),
)

if datum:
    if datum not in st.session_state:
        st.session_state[datum] = {}
    monatsstart, monatsende = monatsbereich(datum)
    with get_db_connection() as session:
        # user und payments werden unten für jede Rechnung gebraucht und deshalb
        # gleich mitgeladen – sonst löst jede Rechnung zwei Nachladequeries aus.
        invoices = session.scalars(
            select(Invoice)
            .join(Invoice.user)
            .options(
                contains_eager(Invoice.user),
                selectinload(Invoice.payments),
            )
            .where(Invoice.monat >= monatsstart, Invoice.monat < monatsende)
            # offene Rechnungen zuerst: "bezahlt IS NOT NULL" ist 0 für offene,
            # 1 für bezahlte; innerhalb der Gruppen nach Nachname.
            .order_by(Invoice.bezahlt.isnot(None), User.name)
        ).all()

        # wenn für den gewählten Monat noch keine Rechnungen gebucht wurden
        if len(invoices) < 1:
            st.write("Es wurden noch keine Rechnungen für diesen Monat gebucht.")
            if "users" not in st.session_state[datum]:
                st.session_state[datum]["users"] = (
                    session.scalars(
                        select(User)
                        .options(
                            selectinload(
                                User.payments.and_(
                                    Payment.ts >= monatsstart,
                                    Payment.ts < monatsende,
                                    or_(
                                        Payment.typ == "Einkauf",
                                        Payment.typ == "Korrektur",
                                        Payment.typ == "Auszahlung",
                                    ),
                                )
                            ),
                            selectinload(
                                User.logs.and_(
                                    Log.ts >= monatsstart, Log.ts < monatsende
                                )
                            ),
                        )
                        .order_by(User.name)
                    )
                ).all()

            # Alle Saldi in einer Query, statt zweimal pro Person einzeln.
            # no_autoflush, weil weiter unten noch nicht gebuchte Invoice-Objekte
            # an die User gehängt werden: ein Autoflush würde diese Rechnungen
            # vorzeitig in die Datenbank schreiben.
            with session.no_autoflush:
                saldi = get_saldi(session)

            # Gesamtabrechnung
            st.subheader("Gesamtabrechnung")
            mitgliederkaffees = 0
            gastkaffees = 0
            zahlungssumme = quantize_decimal("0")
            for user in st.session_state[datum]["users"]:
                session.add(user)
                mitgliederkaffees += sum(
                    log.anzahl for log in user.logs if user.mitglied
                )
                gastkaffees += sum(log.anzahl for log in user.logs if not user.mitglied)
                zahlungssumme += sum(
                    payment.betrag
                    for payment in user.payments
                    if payment.typ in ["Einkauf", "Korrektur"]
                )

            monatseinnahmen = mitgliederkaffees * quantize_decimal(
                st.secrets.KAFFEEPREIS_MITGLIED
            ) + gastkaffees * quantize_decimal(st.secrets.KAFFEEPREIS_GAST)
            ueberschuss = monatseinnahmen - zahlungssumme

            st.write("Mitgliederkaffees:", mitgliederkaffees)
            st.write("Gastkaffees:", gastkaffees)
            st.write("Gesamtkaffees:", mitgliederkaffees + gastkaffees)
            st.write("Monatseinnahmen: € ", monatseinnahmen)
            st.write("Verbrauchskosten: € ", zahlungssumme)
            st.write("Überschuss: € ", ueberschuss)

            # Zahlungen
            st.subheader("Zahlungen")

            payment_list = []

            for user in st.session_state[datum]["users"]:
                payment_list.extend(
                    [
                        {
                            "Datum": payment.ts,
                            "Betreff": payment.betreff,
                            "Betrag": payment.betrag,
                            "Typ": payment.typ,
                            "Nutzer": user.name,
                        }
                        for payment in user.payments
                        if payment.typ in ["Einkauf", "Korrektur", "Auszahlung"]
                    ]
                )

            st.dataframe(
                payment_list,
                column_config={
                    "Betrag": st.column_config.NumberColumn(format="€ %.2f"),
                    "Datum": st.column_config.DatetimeColumn(format="DD.MM.YYYY"),
                },
            )
            st.subheader("Einzelabrechnungen")
            with st.spinner("Einzelabrechnungen werden erstellt …"):
                if "invoices" not in st.session_state[datum]:
                    monatsliste(datum, saldi)
                show_liste = []

                table = st.dataframe(
                    [
                        {
                            "Name": abrechnung.user.name,
                            "Zahlbetrag": quantize_decimal(abrechnung.gesamtbetrag),
                            "Kaffeeanzahl": abrechnung.kaffee_anzahl,
                            "Kaffeekosten": abrechnung.kaffee_preis,
                            "Einkäufe": abrechnung.payment_betrag,
                            "Guthaben alt": saldi.get(
                                abrechnung.user_id, quantize_decimal("0")
                            ),
                        }
                        for abrechnung in st.session_state[datum]["invoices"]
                    ],
                    column_config={
                        "Zahlbetrag": st.column_config.NumberColumn(format="€ %g"),
                        "Kaffeekosten": st.column_config.NumberColumn(format="€ %g"),
                        "Einkäufe": st.column_config.NumberColumn(format="€ %g"),
                        "Guthaben alt": st.column_config.NumberColumn(format="€ %g"),
                    },
                )
                monatsabrechnung = st.button(
                    f"Monatsabrechnung {uebersetzungen[datum.strftime("%B")]} erstellen"
                )
                if monatsabrechnung:
                    confirm_monatsabrechnung()
        # wenn für den gewählten Monat bereits Rechnungen gebucht wurden
        elif len(invoices) > 0:
            st.subheader("Gebuchte Rechnungen")

            offen = [r for r in invoices if not r.bezahlt]
            offener_betrag = sum((r.gesamtbetrag for r in offen), Decimal("0.00"))
            spalte1, spalte2, spalte3 = st.columns(3)
            spalte1.metric("Rechnungen", str(len(invoices)))
            spalte2.metric("davon bezahlt", str(len(invoices) - len(offen)))
            spalte3.metric("offener Betrag", euro(offener_betrag))

            # Die Zeilenreihenfolge merken: der Klick-Callback bekommt nur eine
            # Zeilennummer und muss daraus die Rechnung auflösen.
            # Zeilenreihenfolge merken: der Klick-Callback bekommt nur eine
            # Zeilennummer und muss daraus die Rechnung auflösen.
            st.session_state["rechnungs_ids"] = [r.id for r in invoices]

            # Bewusst schmal gehalten: die Tabelle muss in die Seitenbreite
            # passen, ohne dass die Knöpfe abgeschnitten werden. Kaffeekosten,
            # Einkäufe und das Bezahldatum stehen im Detail-Dialog.
            tabelle = pd.DataFrame(
                [
                    {
                        "Status": "✅ bezahlt" if r.bezahlt else "❌ offen",
                        "Name": r.user.name,
                        "Kaffees": r.kaffee_anzahl,
                        "Zahlbetrag": r.gesamtbetrag,
                        # Leere Zelle = kein Knopf: bezahlte Rechnungen
                        # bekommen keinen Bezahlt-Knopf mehr.
                        "buchen": None if r.bezahlt else "buchen",
                        "details": "Details",
                    }
                    for r in invoices
                ]
            )

            st.dataframe(
                tabelle,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn(width="small"),
                    "Kaffees": st.column_config.NumberColumn(width="small"),
                    "Zahlbetrag": st.column_config.NumberColumn(format="€ %.2f"),
                    "buchen": st.column_config.ButtonColumn(
                        "Zahlungseingang",
                        width="medium",
                        type="primary",
                        on_click=rechnung_bezahlt_markieren,
                        key="klick_bezahlt",
                    ),
                    "details": st.column_config.ButtonColumn(
                        "",
                        width="small",
                        type="tertiary",
                        on_click=rechnung_details_merken,
                        key="klick_details",
                    ),
                },
            )

            if st.session_state.get("details_rechnung"):
                zeige_rechnungsdetails(st.session_state.pop("details_rechnung"))
