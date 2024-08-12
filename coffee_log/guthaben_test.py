import streamlit as st

from database.models import User, Payment
from sqlalchemy import select

conn = st.connection("coffee_counter", type="sql")

namensliste = ["Reichheim", "Friesel", "Wendler"]
for name in namensliste:
    st.subheader(f"Abrechnung {name}")
    with conn.session as session:
        nutzer = session.scalar(select(User).where(User.name == name))
        st.write("Saldo: ", nutzer.get_saldo(conn))
        st.write("Invoices:")
        invoices = nutzer.get_invoices(conn)
        invoice_summe = 0
        for invoice in invoices:
            invoice_summe += invoice.gesamtbetrag
            st.write(invoice.monat, invoice.gesamtbetrag, "Kaffees: ", invoice.kaffee_anzahl, "bezahlt ", invoice.bezahlt)

        st.write("Payments:")
        payments = session.scalars(
                select(Payment).where(
                    Payment.user_id == nutzer.id,
                )
            ).all()
        gesamtbetrag = 0
        for payment in payments:
            gesamtbetrag += payment.betrag
            st.write(payment.betrag)
        st.write("Gesamtbetrag Payments: ", gesamtbetrag)
        