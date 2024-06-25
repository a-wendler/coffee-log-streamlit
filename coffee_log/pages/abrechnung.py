from datetime import datetime
from typing import List, TypedDict, Optional, Union
from decimal import Decimal
import pandas as pd
import streamlit as st
from sqlalchemy import select, extract, func, or_
from menu import menu_with_redirect
from pages.monatsuebersicht import get_first_days_of_last_six_months
from pages.mail import send_invoice
from models import Log, User, Payment, Invoice


def quantize_decimal(value: Union[Decimal, int, float, str]) -> Decimal:
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")
    return Decimal(value).quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")


def get_subscription_fee() -> Decimal:
    # Get the number of members
    with conn.session as get_subscription_fee_session:
        num_members_stmt = select(func.count(User.id)).where(User.mitglied == 1)
        num_members = get_subscription_fee_session.scalar(num_members_stmt)

    if num_members < 1:
        return 0
    fee = quantize_decimal(st.secrets.MIETE) / num_members
    return quantize_decimal(fee)


def gesamt_abrechnung(datum):
    st.header("Gesamtabrechnung")

    st.write(
        "Mitgliederkaffees:",
        get_coffee_number(monat=datum, gruppe="mitglied"),
    )
    st.write(
        "Gastkaffees:",
        get_coffee_number(monat=datum, gruppe="gast"),
    )
    st.write(
        "Gesamtkaffees:",
        get_coffee_number(monat=datum),
    )

    with conn.session as local_session:
        payments = local_session.scalars(
            select(Payment)
            .join(User)
            .where(
                extract("month", Payment.ts) == datum.month,
                extract("year", Payment.ts) == datum.year,
                or_(
                    Payment.typ == "Einkauf",
                    Payment.typ == "Korrektur",
                    Payment.typ == "Auszahlung",
                ),
            )
        ).all()
        payment_list = []
        for payment in payments:
            payment_list.append(
                {
                    "Datum": payment.ts,
                    "Betreff": payment.betreff,
                    "Betrag": payment.betrag,
                    "Typ": payment.typ,
                    "Nutzer": payment.user.name,
                }
            )
    payments_df = pd.DataFrame().from_records(payment_list)
    st.subheader("Zahlungen")
    st.dataframe(
        payments_df,
        column_config={"Betrag": st.column_config.NumberColumn(format="€ %.2f")},
    )
    st.write("Verbrauchskosten: €", get_payment_sum(datum))
    st.write("Miete: €", quantize_decimal(st.secrets.MIETE))
    st.write(
        "Gesamtkosten: €", get_payment_sum(datum) + quantize_decimal(st.secrets.MIETE)
    )
    st.write("Mitgliederkaffeepreis: €", get_member_coffee_price(datum))


class coffee_number_kwargs(TypedDict, total=False):
    monat: Optional[datetime] = datetime.now()
    gruppe: Optional[str] = "all"
    user_id: Optional[int] = None


def get_coffee_number(**kwargs: coffee_number_kwargs) -> int:
    """
    Ermittelt die Anzahl von Kaffees.

    Optionale Keyword Arguments:

    monat: Optional[datetime], default datetime.now(), beliebiges Datum aus einem Monat. Es werden die Kaffees dieses Monats ermittelt. Standard ist der aktuelle Monat.

    gruppe: Optional[str], default 'all', Optionen: 'all', 'mitglied', 'gast', gibt die Gruppe an, für die die Kaffees ermittelt werden sollen, wenn Argument nicht übergeben, werden alle Gruppen ermittelt

    user_id: Optional[int], default None; gibt Kaffees für einen User zurück, wenn Argument übergeben, sonst Kaffees für alle User. Wenn Argument übergeben, wird 'gruppe' ignoriert.

    return: int: Anzahl von Kaffees
    """
    # Default values für kwargs
    monat = kwargs.get("monat", datetime.now())
    gruppe = kwargs.get("gruppe", "all")
    user_id = kwargs.get("user_id", None)

    # Checken, ob die Argumente die richtigen Typen haben
    if not isinstance(monat, datetime):
        raise ValueError("Argument 'monat' muss ein datetime-Objekt sein")
    if not gruppe in ["all", "mitglied", "gast"]:
        raise ValueError("Argument 'gruppe' muss 'all', 'mitglied' oder 'gast' sein")
    if user_id and not isinstance(user_id, int):
        raise ValueError("Argument 'user_id' muss ein Integer sein")

    with conn.session as coffee_number_session:
        coffee_number_stmt = select(func.sum(Log.anzahl)).where(
            extract("month", Log.ts) == monat.month,
            extract("year", Log.ts) == monat.year,
        )

        if user_id:
            coffee_number_stmt = coffee_number_stmt.where(Log.user_id == user_id)
            kaffeemenge = coffee_number_session.scalar(coffee_number_stmt)
            if kaffeemenge:
                if kaffeemenge > 0:
                    return kaffeemenge

        if gruppe == "mitglied":
            coffee_number_stmt = coffee_number_stmt.join(User).where(User.mitglied == 1)
        if gruppe == "gast":
            coffee_number_stmt = coffee_number_stmt.join(User).where(User.mitglied == 0)

        kaffeemenge = coffee_number_session.scalar(coffee_number_stmt)

    if kaffeemenge:
        if kaffeemenge > 0:
            return kaffeemenge
    return 0


def get_payment_sum(month: datetime) -> float:
    with conn.session as get_payment_session:
        betrag = (
            get_payment_session.query(func.sum(Payment.betrag))
            .filter(
                extract("month", Payment.ts) == month.month,
                extract("year", Payment.ts) == month.year,
            )
            .scalar()
        )
    if betrag:
        if betrag > 0:
            return quantize_decimal(betrag)
    return quantize_decimal("0")


def get_payments(month: datetime) -> List[Payment]:
    with conn.session as local_session:
        return (
            local_session.query(Payment)
            .filter(
                extract("month", Payment.ts) == month.month,
                extract("year", Payment.ts) == month.year,
            )
            .all()
        )


def get_member_coffee_price(month: datetime) -> Decimal:
    """
    Ermittelt den Preis für einen Mitgliederkaffee.
    """
    member_coffees = get_coffee_number(monat=month, gruppe="mitglied")
    guest_coffees = get_coffee_number(monat=month, gruppe="gast")
    payment_sum = get_payment_sum(month)

    gesamtkosten = quantize_decimal(st.secrets.MIETE) + payment_sum
    price = (gesamtkosten - guest_coffees) / member_coffees
    return quantize_decimal(price)


class einzelabrechnung_kwargs(TypedDict):
    datum: Optional[datetime] = datetime.now()
    user_id: int


def einzelabrechnung(**kwargs: einzelabrechnung_kwargs) -> Invoice:
    """
    Erstellt eine Einzelabrechnung für einen Nutzer.

    Keyword Arguments:

    monat: Optional[datetime], default datetime.now(), beliebiges Datum aus einem Monat. Es werden die Kaffees dieses Monats ermittelt. Standard ist der aktuelle Monat.
    user_id: int, ID des Nutzers, für den die Abrechnung erstellt werden soll. Muss übergeben werden.

    returns: Invoice-Objekt
    """
    # Default values für kwargs
    datum = kwargs.get("datum", datetime.now())
    user_id = kwargs.get("user_id")

    if not user_id:
        raise ValueError("Argument 'user_id' muss übergeben werden")

    # Checken, ob die Argumente die richtigen Typen haben
    if not isinstance(datum, datetime):
        raise ValueError("Argument 'monat' muss ein datetime-Objekt sein")
    if not isinstance(user_id, int):
        raise ValueError("Argument 'user_id' muss ein Integer sein")

    kaffee_anzahl = get_coffee_number(monat=datum, user_id=user_id)

    with conn.session as einzelabrechnung_session:
        user = einzelabrechnung_session.scalar(select(User).where(User.id == user_id))

        member_status = user.mitglied

        payments_stmt = select(Payment).where(
            extract("month", Payment.ts) == datum.month,
            extract("year", Payment.ts) == datum.year,
            Payment.user_id == user_id,
        )

        payments = einzelabrechnung_session.scalars(payments_stmt).all()

        betrag_stmt = select(func.sum(Payment.betrag)).where(
            extract("month", Payment.ts) == datum.month,
            extract("year", Payment.ts) == datum.year,
            Payment.user_id == user_id,
        )

        payment_betrag = einzelabrechnung_session.scalar(betrag_stmt)
        if not payment_betrag:
            payment_betrag = quantize_decimal("0")

        miete = get_subscription_fee()

        if member_status == 1:
            kaffee_preis = get_member_coffee_price(datum) * kaffee_anzahl
            gesamtbetrag = quantize_decimal((kaffee_preis + miete - payment_betrag))
        if member_status == 0:
            kaffee_preis = kaffee_anzahl * quantize_decimal(st.secrets.KAFFEEPREIS_GAST)
            gesamtbetrag = quantize_decimal((kaffee_preis - payment_betrag))

    return Invoice(
        kaffee_anzahl=kaffee_anzahl,
        miete=miete,
        kaffee_preis=kaffee_preis,
        payment_betrag=payment_betrag,
        gesamtbetrag=gesamtbetrag,
        monat=datum,
        payments=payments,
        user_id=user_id,
        user=user,
        ts=datetime.now(),
    )


class monatsliste_kwargs(TypedDict):
    datum: Optional[datetime] = datetime.now()


@st.cache_data
def monatsliste(**kwargs: monatsliste_kwargs):
    # Default values für kwargs
    datum = kwargs.get("datum", datetime.now())

    # Checken, ob die Argumente die richtigen Typen haben
    if not isinstance(datum, datetime):
        raise ValueError("Argument 'monat' muss ein datetime-Objekt sein")

    with conn.session as local_session:
        stmt = (
            select(User)
            .filter(User.status == "active")
            .order_by(User.name, User.vorname)
        )
        users = local_session.scalars(stmt).all()
        abrechnungen_list = []
        for user in users:
            rechnung = einzelabrechnung(monat=datum, user_id=user.id)
            abrechnungen_list.append(rechnung)
        return abrechnungen_list


def einzelabrechnung_web(datum):
    st.header("Einzelabrechnung")
    with conn.session as local_session:
        user_choice = st.selectbox(
            "Nutzer",
            [
                user[0].id
                for user in local_session.execute(
                    select(User).filter(User.mitglied == 1)
                ).all()
            ],
            format_func=lambda x: local_session.execute(
                select(User).filter(User.id == x)
            )
            .first()[0]
            .name,
            key="user",
        )
        logs = local_session.execute(
            select(Log).filter(
                extract("month", Log.ts) == datum.month,
                extract("year", Log.ts) == datum.year,
                Log.user_id == user_choice,
            )
        ).all()
        log_list = []
        for log in logs:
            log_list.append(
                {
                    "Datum": log[0].ts,
                    "Anzahl": log[0].anzahl,
                }
            )
        logs_df = pd.DataFrame().from_records(log_list)
        st.write(logs_df)
    anzahl_kaffees = logs_df.Anzahl.sum()
    miete_anteilig = get_subscription_fee()

    st.write("Anzahl Kaffees:", anzahl_kaffees)
    st.write("Miete anteilig:", miete_anteilig)

def monatsbuchung(datum):
    with conn.session as local_session:
        try:

            for invoice in monats_liste:
                payments = local_session.scalars(select(Payment).where(
                        extract("month", Payment.ts) == datum.month,
                        extract("year", Payment.ts) == datum.year,
                        Payment.user == invoice.user,
                    )).all()
                # st.write(type(payments))
                invoice.payments = payments
                invoice.monat = datum
                invoice.ts = datetime.now()
                local_session.add(invoice)
            
            reichheim = local_session.scalar(select(User).where(User.name == "Reichheim"))
            miete = Payment(
                betrag=quantize_decimal(st.secrets.MIETE),
                betreff=f"Miete {datum.strftime('%B %Y')}",
                typ="Miete",
                ts=datum,
                user=reichheim,
                user_id=reichheim.id,
            )
            local_session.add(miete)
            local_session.commit()
            st.success("Buchung erfolgreich")
        except Exception as e:
            st.error("Fehler bei der Buchung")
            st.error(e)
            local_session.rollback()

@st.experimental_dialog("Monatsabrechnung erstellen?")
def confirm_monatsabrechnung():
    st.write("Wollen Sie die Monatsabrechnung wirklich erstellen und die Rechnungen einbuchen?")
    if st.button("Ja"):
        monatsbuchung(datum)
    if st.button("Nein"):
        st.rerun()

def send_invoice_mail(id: int):
    mailversand = send_invoice(id)
    
    if mailversand:
        st.session_state.invoice_status[id] = mailversand
    else:
        st.session_state.invoice_status[id] = "Fehler beim Versand der E-Mail" 

def send_all_invoices(liste: List[Invoice]):
    for invoice in liste:
        if not invoice.email_versand:
            mailversand = send_invoice(invoice.id)
            if mailversand:
                st.session_state.invoice_status[invoice.id] = mailversand
            else:
                st.session_state.invoice_status[invoice.id] = "Fehler beim Versand der E-Mail"

def mark_invoice_paid(id: int):
    with conn.session as session:
        invoice = session.scalar(select(Invoice).where(Invoice.id == id))
        invoice.bezahlt = datetime.now()
        monat = datetime.strptime(invoice.monat, "%Y-%m-%d %H:%M:%S")
        monat = uebersetzungen[monat.strftime("%B")] + " " + monat.strftime("%Y")
        payment = Payment(
            betrag=invoice.gesamtbetrag,
            betreff=f"Rechnung {monat}",
            typ="Einzahlung",
            ts=datetime.now(),
            user_id=invoice.user_id,
            invoice_id=invoice.id,
        )
        session.add(payment)
        session.commit()
        st.session_state.invoice_status[id] = "Rechnung als bezahlt markiert"

# Streamlit app layout
menu_with_redirect()
if "invoice_status" not in st.session_state:
    st.session_state.invoice_status = {}
conn = st.connection("coffee_counter", type="sql")
st.subheader("Abrechnung")

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
    gesamt_abrechnung(datum)
    st.write(datum)
    st.subheader("Einzelabrechnungen")
    with conn.session as session:
        anzahl_invoices = session.scalar(
            select(func.count(Invoice.id)).where(
                extract("month", Invoice.monat) == datum.month,
                extract("year", Invoice.monat) == datum.year,
            )
        )
        st.write("Anzahl gebuchte Einzelabrechnungen:", anzahl_invoices)
    if anzahl_invoices < 1:
        with st.spinner("Einzelabrechnungen werden erstellt …"):
            monats_liste = monatsliste(datum=datum)
            show_liste = []
            for abrechnung in monats_liste:
                show_liste.append(
                    {
                        "Name": abrechnung.user.name,
                        "Monatsbetrag": quantize_decimal(abrechnung.gesamtbetrag),
                        "Kaffeeanzahl": abrechnung.kaffee_anzahl,
                        "Gutschriften": abrechnung.payment_betrag,
                    }
                )

            df = pd.DataFrame().from_records(show_liste)
            table = st.dataframe(
                df,
                column_config={
                    "Monatsbetrag": st.column_config.NumberColumn(format="€ %g")
                },
            )
            st.write("Gesamtsumme:", df.Monatsbetrag.sum())

            monatsabrechnung = st.button(f"Monatsabrechnung {uebersetzungen[datum.strftime("%B")]} erstellen")
            if monatsabrechnung:
                confirm_monatsabrechnung()
    elif anzahl_invoices > 0:
        st.write(
            f"Abrechnungen für {uebersetzungen[datum.strftime('%B')]} wurden bereits gebucht"
        )
        with conn.session as session:
            monats_liste = session.scalars(
                select(Invoice).where(
                    extract("month", Invoice.monat) == datum.month,
                    extract("year", Invoice.monat) == datum.year,
                )
            ).all()
            show_liste = []
            for abrechnung in monats_liste:
                if abrechnung.bezahlt:
                    bezahlt_icon = "✅"
                else:
                    bezahlt_icon = "❌"
                if abrechnung.email_versand:
                    email_icon = "📧"
                else:
                    email_icon = ""
                
                with st.expander(label=f"{bezahlt_icon} {email_icon} {abrechnung.user.name}"):
                    st.write("Monatsbetrag:", abrechnung.gesamtbetrag)
                    st.write("Kaffeeanzahl:", abrechnung.kaffee_anzahl)
                    st.write("Gutschriften:", abrechnung.payment_betrag)
                    st.write("Erstellt:", abrechnung.ts)
                    st.write("E-Mailversand:", abrechnung.email_versand)
                    st.write("Bezahlt:", abrechnung.bezahlt)
                    st.write("Zahlungen:")
                    for payment in abrechnung.payments:
                        st.write(payment.betrag, payment.betreff, payment.ts)

                    st.button("Rechnung senden", key=f"invoice_{abrechnung.id}",on_click=send_invoice_mail, args=(abrechnung.id,))
                    st.write(st.session_state.invoice_status.get(abrechnung.id, ""))

                    st.button("Rechnung als bezahlt markieren", key=f"paid_{abrechnung.id}", on_click=mark_invoice_paid, args=(abrechnung.id,))
            
            st.button("Alle Rechnungen senden", key="send_all", on_click=send_all_invoices, args=(monats_liste,))
            st.write("Wenn ein Nutzer schon eine Rechnung per E-Mail erhalten hat, wird sie über diesen Button nicht noch einmal versandt. Individueller Neuversand ist in den jeweiligen Rechnungs-Boxen möglich.")
