"""Module for editing user data."""

import os
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlsplit, urlunsplit

import streamlit as st
import pandas as pd
from loguru import logger
from database.models import STATUS_WERTE, User
from database.queries import get_abschluss_daten
from sqlalchemy import select
from db import get_connection
from helpers import euro, is_valid_email, monatsname
from nutzer_verwaltung import (
    AUSGEBUCHT,
    BEZAHLT,
    NutzerFehler,
    abschluss_buchen,
    loeschen,
    reaktivieren,
    stilllegen,
)


def token_link(token):
    """Link zum Weitergeben – für eine Einladung wie für ein neues Kennwort.

    Schema und Host kommen aus der URL, mit der der Admin gerade arbeitet; so
    stimmt der Link in der Testinstanz genauso wie in der echten App. Der Pfad
    entfällt: app.py wertet den Token auf jeder Seite aus, und die Startseite
    ist die kürzeste Adresse zum Vorlesen oder Abtippen.
    """
    teile = urlsplit(st.context.url)
    return urlunsplit((teile.scheme, teile.netloc, "/", f"token={token}", ""))


def linkkasten(ueberschrift, email, link, hinweis):
    """Einheitlicher Kasten, aus dem ein Link kopiert werden kann."""
    st.success(ueberschrift)
    st.markdown(f"**Bitte schicken Sie diesen Link an {email}.** {hinweis}")
    st.code(link, language=None)
    st.caption("Zum Kopieren auf das Symbol rechts im Feld klicken.")


def neuen_nutzer_anlegen(vorname, name, email, mitglied, ist_admin):
    """Legt ein Konto an und merkt sich den Einladungslink für die Anzeige.

    Das Konto bleibt bis zum Klick auf den Link im Status "new": Es gibt noch
    kein Kennwort, deshalb steht in ``code`` ein Zufallswert, der zu keiner
    Eingabe passt. Die Spalte ist NOT NULL und unique, ein Platzhalter wie ""
    würde das zweite Konto blockieren.

    Verschickt wird nichts: Den Link gibt der Admin selbst weiter.
    """
    token = "activate_" + sha256(os.urandom(60)).hexdigest()
    with conn.session as session:
        try:
            user = User(
                code=sha256(os.urandom(60)).hexdigest(),
                name=name,
                vorname=vorname,
                email=email,
                admin=1 if ist_admin else 0,
                mitglied=1 if mitglied else 0,
                ts=datetime.now(),
                token=token,
                status="new",
            )
            session.add(user)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Nutzer {email} konnte nicht angelegt werden: {e}")
            st.error(
                "Der Nutzer konnte nicht angelegt werden. "
                "Ist die E-Mail-Adresse bereits vergeben?"
            )
            return

    logger.success(f"Nutzer {email} angelegt, Einladung wartet auf Weitergabe.")
    # In den Session State, nicht direkt anzeigen: Der Kasten soll auch nach
    # dem nächsten Klick auf der Seite noch stehen, bis der Admin ihn schließt.
    st.session_state["neue_einladung"] = {
        "person": f"{vorname} {name}",
        "email": email,
        "link": token_link(token),
    }


def einladung_schliessen():
    st.session_state.pop("neue_einladung", None)


def einladung_anzeigen():
    """Zeigt den Einladungslink des zuletzt angelegten Nutzers."""
    einladung = st.session_state.get("neue_einladung")
    if not einladung:
        return

    with st.container(border=True):
        linkkasten(
            f"{einladung['person']} wurde angelegt.",
            einladung["email"],
            einladung["link"],
            "Die Person vergibt darüber ihr Kennwort und aktiviert damit ihr "
            "Konto. Der Link funktioniert nur ein einziges Mal; solange er nicht "
            "benutzt wurde, finden Sie ihn unter „Offene Einladungen“ wieder.",
        )
        st.button("Schließen", on_click=einladung_schliessen)


def offene_einladungen():
    """Links aller Konten, die noch nicht aktiviert wurden.

    Ohne diese Liste wäre ein verlorener Link nicht zu ersetzen: Das Konto
    existiert, lässt sich aber nie aktivieren.
    """
    with conn.session as session:
        wartende = list(
            session.scalars(
                select(User)
                .where(User.status == "new", User.token.is_not(None))
                .order_by(User.ts)
            )
        )

    with st.expander(f"Offene Einladungen ({len(wartende)})"):
        if not wartende:
            st.write("Alle angelegten Konten sind aktiviert.")
            return
        st.write(
            "Diese Konten warten noch darauf, dass ihr Link benutzt wird. Sie "
            "können ihn erneut verschicken:"
        )
        for user in wartende:
            st.markdown(f"**{user.vorname} {user.name}** – {user.email}")
            st.code(token_link(user.token), language=None)


def kennwort_link_schliessen():
    st.session_state.pop("neuer_kennwort_link", None)


def kennwort_link_erzeugen(user_id):
    """Setzt einen frischen Reset-Token und merkt sich den Link zum Anzeigen.

    Das alte Kennwort bleibt gültig, bis die Person über den Link ein neues
    vergibt – ein versehentlich erzeugter Link sperrt also niemanden aus.
    """
    with conn.session as session:
        user = session.get(User, user_id)
        if user is None or user.status != "active":
            st.error("Das Konto existiert nicht mehr oder ist nicht aktiv.")
            return
        try:
            user.token = "reset_" + sha256(os.urandom(60)).hexdigest()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Kennwort-Link für {user.email} fehlgeschlagen: {e}")
            st.error("Der Link konnte nicht erzeugt werden.")
            return

        logger.success(f"Kennwort-Link für {user.email} erzeugt.")
        st.session_state["neuer_kennwort_link"] = {
            "person": f"{user.vorname} {user.name}",
            "email": user.email,
            "link": token_link(user.token),
        }


def kennwort_link_formular():
    """Auswahl der Person, für die ein Kennwort-Link erzeugt wird.

    Bewusst neben der Tabelle statt als Knopf darin: Ein Klick in der Tabelle
    löst einen Rerun aus und wirft ungespeicherte Änderungen weg.
    """
    with conn.session as session:
        aktive = list(
            session.scalars(
                select(User).where(User.status == "active").order_by(User.name)
            )
        )

    if not aktive:
        st.write("Es gibt noch keine aktiven Konten.")
        return

    namen = {u.id: f"{u.name}, {u.vorname} ({u.email})" for u in aktive}
    st.write(
        "Wer sein Kennwort vergessen hat, bekommt hier einen Link, über den er "
        "selbst ein neues vergibt. Schicken Sie ihn der Person direkt."
    )
    gewaehlt = st.selectbox(
        "Person", options=list(namen), format_func=lambda i: namen[i]
    )
    st.button(
        "Kennwort-Link erzeugen",
        on_click=kennwort_link_erzeugen,
        args=(gewaehlt,),
    )


def kennwort_link_anzeigen():
    """Zeigt den zuletzt erzeugten Kennwort-Link."""
    kennwort_link = st.session_state.get("neuer_kennwort_link")
    if not kennwort_link:
        return

    with st.container(border=True):
        linkkasten(
            f"Kennwort-Link für {kennwort_link['person']} erzeugt.",
            kennwort_link["email"],
            kennwort_link["link"],
            "Das bisherige Kennwort gilt so lange weiter, bis die Person über "
            "den Link ein neues vergeben hat. Der Link funktioniert nur ein "
            "einziges Mal.",
        )
        st.button("Schließen", on_click=kennwort_link_schliessen)


def neuen_nutzer_formular():
    """Formular zum Anlegen eines neuen Nutzers."""
    # kein clear_on_submit: sonst sind bei einer abgelehnten Eingabe (Tippfehler
    # in der E-Mail, fehlendes Pflichtfeld) alle Felder wieder leer.
    with st.form(key="neuer_nutzer"):
        vorname = st.text_input("Vorname")
        name = st.text_input("Nachname")
        email = st.text_input("E-Mail")
        mitglied = st.checkbox(
            "Mitglied",
            help="Ist die Person zahlendes Mitglied der Mietergemeinschaft?",
        )
        ist_admin = st.checkbox(
            "Admin",
            help="Hat die Person Zugriff auf Abrechnung, Nutzerdaten und Einkäufe?",
        )
        st.write("Vorname, Nachname und E-Mail sind Pflichtfelder.")
        submit = st.form_submit_button("Nutzer anlegen", type="primary")

    if submit:
        if not vorname or not name or not email:
            st.error("Vorname, Nachname und E-Mail sind Pflichtfelder.")
        elif not is_valid_email(email):
            st.error("Bitte geben Sie eine gültige E-Mail-Adresse ein.")
        else:
            neuen_nutzer_anlegen(vorname, name, email, mitglied, ist_admin)


def stilllegen_ausfuehren(user_id):
    with conn.session as session:
        try:
            name = stilllegen(session, user_id)
        except NutzerFehler as fehler:
            st.error(str(fehler))
            return
        except Exception as fehler:
            session.rollback()
            logger.error(f"Stilllegen von {user_id} fehlgeschlagen: {fehler}")
            st.error("Das Konto konnte nicht stillgelegt werden.")
            return

    logger.success(f"Konto {user_id} stillgelegt.")
    st.success(
        f"{name} wurde stillgelegt und kann sich nicht mehr anmelden. Alle "
        "Kaffees und Zahlungen bleiben in den Auswertungen."
    )


def reaktivieren_ausfuehren(user_id):
    with conn.session as session:
        try:
            name = reaktivieren(session, user_id)
        except NutzerFehler as fehler:
            st.error(str(fehler))
            return
        except Exception as fehler:
            session.rollback()
            logger.error(f"Reaktivieren von {user_id} fehlgeschlagen: {fehler}")
            st.error("Das Konto konnte nicht wieder aktiviert werden.")
            return

    logger.success(f"Konto {user_id} wieder aktiviert.")
    st.success(
        f"{name} ist wieder aktiv und kann sich mit dem alten Kennwort anmelden."
    )


def abschluss_ausfuehren(user_id, art):
    with conn.session as session:
        try:
            betrag = abschluss_buchen(session, user_id, art)
        except NutzerFehler as fehler:
            st.error(str(fehler))
            return
        except Exception as fehler:
            session.rollback()
            logger.error(f"Abschluss für {user_id} fehlgeschlagen: {fehler}")
            st.error("Die Schlussabrechnung konnte nicht gebucht werden.")
            return

    logger.success(f"Abschluss für Konto {user_id} gebucht: {betrag} ({art}).")
    st.success(f"Schlussabrechnung gebucht: {euro(betrag)}. Der Saldo steht auf 0.")


def loeschen_ausfuehren(user_id):
    with conn.session as session:
        try:
            name = loeschen(session, user_id)
        except NutzerFehler as fehler:
            st.error(str(fehler))
            return
        except Exception as fehler:
            session.rollback()
            logger.error(f"Löschen von {user_id} fehlgeschlagen: {fehler}")
            st.error("Das Konto konnte nicht gelöscht werden.")
            return

    logger.success(f"Konto {user_id} gelöscht.")
    st.success(f"{name} wurde gelöscht.")


def stand_anzeigen(daten):
    """Saldo, offene Rechnungen und noch nicht abgerechnete Kaffees."""
    spalte1, spalte2, spalte3 = st.columns(3)
    spalte1.metric("Saldo", euro(daten.saldo))
    spalte2.metric(
        "offene Rechnungen",
        str(daten.offene_rechnungen),
        help=f"Summe: {euro(daten.offener_betrag)}",
    )
    spalte3.metric("nicht abgerechnete Kaffees", str(daten.unabgerechnete_kaffees))


def ausscheiden_formular():
    """Konto stilllegen: kein Login mehr, Historie bleibt vollständig."""
    eigene_id = st.session_state.user.id
    with conn.session as session:
        aktive = list(
            session.scalars(
                select(User)
                .where(User.status == "active", User.id != eigene_id)
                .order_by(User.name)
            )
        )

    if not aktive:
        st.write("Es gibt keine weiteren aktiven Konten.")
        return

    st.write(
        "Wer die Firma verlässt, wird stillgelegt statt gelöscht: Die Person "
        "kann sich nicht mehr anmelden und bekommt keine neuen Rechnungen, ihre "
        "Kaffees und Zahlungen zählen aber weiter in allen Summen mit. Das "
        "eigene Konto steht nicht zur Auswahl."
    )
    namen = {u.id: f"{u.name}, {u.vorname} ({u.email})" for u in aktive}
    gewaehlt = st.selectbox(
        "Person",
        options=list(namen),
        format_func=lambda i: namen[i],
        key="ausscheiden_auswahl",
    )

    with conn.session as session:
        daten = get_abschluss_daten(session, gewaehlt)
    if daten is None:
        return

    stand_anzeigen(daten)
    if not daten.abschlussfaehig:
        monate = ", ".join(monatsname(m) for m in daten.unabgerechnete_monate)
        st.info(
            f"Aus {monate} sind noch Kaffees offen. Legen Sie das Konto ruhig "
            "jetzt still - die Schlussabrechnung ist danach möglich, sobald die "
            "Monatsabrechnung gelaufen ist."
        )

    st.button(
        "Konto stilllegen",
        type="primary",
        on_click=stilllegen_ausfuehren,
        args=(gewaehlt,),
    )


def abschluss_block(daten):
    """Schlussabrechnung, Reaktivierung und Löschen für ein stillgelegtes Konto."""
    stand_anzeigen(daten)

    if not daten.abschlussfaehig:
        monate = ", ".join(monatsname(m) for m in daten.unabgerechnete_monate)
        st.warning(
            f"{daten.unabgerechnete_kaffees} Kaffee(s) aus {monate} stehen in "
            "keiner Rechnung. Solange sagt der Saldo nicht die Wahrheit über die "
            "Schulden. Erst die Monatsabrechnung machen, dann hier abschließen."
        )
    elif daten.erledigt:
        st.success("Nichts mehr offen - dieses Konto ist abgeschlossen.")
    else:
        betrag = daten.abschlussbetrag
        if betrag > 0:
            st.write(
                f"**{daten.vorname} {daten.name} schuldet der Kasse "
                f"{euro(betrag)}.** Wie soll der Betrag gebucht werden?"
            )
            beschriftungen = {
                BEZAHLT: "Die Person hat beim Gehen bezahlt (Einzahlung)",
                AUSGEBUCHT: "Die Gemeinschaft trägt den Betrag (Abschluss)",
            }
        else:
            st.write(
                f"**Die Kasse schuldet {daten.vorname} {daten.name} "
                f"{euro(-betrag)}.** Wie soll der Betrag gebucht werden?"
            )
            beschriftungen = {
                BEZAHLT: "Guthaben wurde ausgezahlt (Auszahlung)",
                AUSGEBUCHT: "Guthaben bleibt der Kasse (Abschluss)",
            }

        art = st.radio(
            "Buchungsart",
            options=[BEZAHLT, AUSGEBUCHT],
            format_func=lambda a: beschriftungen[a],
            key=f"abschlussart_{daten.user_id}",
        )
        st.caption(
            "Nur „bezahlt“ und „ausgezahlt“ verändern den Kassenstand. Ein "
            "Abschluss gleicht das Konto aus, ohne dass Geld fließt."
        )
        st.button(
            "Schlussabrechnung buchen",
            type="primary",
            on_click=abschluss_ausfuehren,
            args=(daten.user_id, art),
            key=f"abschluss_{daten.user_id}",
        )

    links, rechts = st.columns(2)
    links.button(
        "Konto wieder aktivieren",
        on_click=reaktivieren_ausfuehren,
        args=(daten.user_id,),
        key=f"reaktivieren_{daten.user_id}",
    )
    if daten.hat_historie:
        rechts.caption(
            "Löschen nicht möglich: Das Konto hat Kaffees oder Zahlungen, die in "
            "den Gesamtsummen stecken."
        )
    else:
        rechts.button(
            "Konto löschen",
            on_click=loeschen_ausfuehren,
            args=(daten.user_id,),
            key=f"loeschen_{daten.user_id}",
        )


def ausgeschiedene():
    """Alle stillgelegten Konten mit ihrem Abschlussstand."""
    with conn.session as session:
        stillgelegte = list(
            session.scalars(
                select(User).where(User.status == "inactive").order_by(User.name)
            )
        )
        stand = [get_abschluss_daten(session, u.id) for u in stillgelegte]

    offen = [d for d in stand if d and not d.erledigt]
    with st.expander(
        f"Ausgeschiedene Nutzer ({len(stand)}), davon {len(offen)} noch abzurechnen"
    ):
        if not stand:
            st.write("Es gibt keine stillgelegten Konten.")
            return
        for daten in stand:
            if daten is None:
                continue
            with st.container(border=True):
                st.markdown(f"**{daten.vorname} {daten.name}**")
                abschluss_block(daten)


def edit_user_data():
    """Edit user data."""
    with conn.session as session:
        users = session.execute(select(User)).scalars().all()
        df = pd.DataFrame().from_records(
            [
                {
                    "id": user.id,
                    "name": user.name,
                    "vorname": user.vorname,
                    "mitglied": user.mitglied,
                    "admin": user.admin,
                    "email": user.email,
                    "status": user.status,
                }
                for user in users
            ]
        )
        edited_df = st.data_editor(
            df,
            column_config={
                "mitglied": st.column_config.CheckboxColumn(
                    "Mitglied",
                    help="Ist die Person zahlendes Mitglied der Mietergemeinschaft?",
                    default=False,
                ),
                "admin": st.column_config.CheckboxColumn(
                    "Admin",
                    help="Hat die Person Zugriff auf Abrechnung, Nutzerdaten und Einkäufe?",
                    default=False,
                ),
                # Feste Auswahl statt Freitext: Ein selbst getippter Status wie
                # "aktiv" sperrt die Person aus, weil der Login genau auf
                # "active" prüft.
                "status": st.column_config.SelectboxColumn(
                    "Status", options=STATUS_WERTE, required=True
                ),
            },
            # "fixed": neue Zeilen legen keinen Nutzer an (das Kennwort fehlt)
            # und gelöschte Zeilen löschen keinen – dafür gibt es das Formular
            # oben bzw. den Status "inactive".
            num_rows="fixed",
            key="data_editor",
            disabled=["id"],
            # Der Zeilenindex von pandas ist keine Information, sondern nur die
            # Position in der Tabelle. Gespeichert wird ohnehin über die Spalte
            # "id", nicht über die Zeilennummer -- das Ausblenden ändert daran
            # nichts.
            hide_index=True,
        )
        if st.button("Änderungen speichern"):
            for _, row in edited_df.iterrows():
                user = session.get(User, int(row["id"]))
                if user is None:
                    session.rollback()
                    st.error(
                        f"Nutzer {row['id']} existiert nicht mehr. "
                        "Bitte laden Sie die Seite neu."
                    )
                    return
                user.name = row["name"]
                user.vorname = row["vorname"]
                user.mitglied = row["mitglied"]
                user.admin = row["admin"]
                user.status = row["status"]
                user.email = row["email"]
            session.commit()
            st.success("Änderungen wurden gespeichert!")


# Streamlit app layout
# menu_with_redirect()
conn = get_connection()
st.subheader("Neuen Nutzer anlegen")
neuen_nutzer_formular()
# nach dem Formular: Beim Anlegen entsteht der Link erst, wenn das Formular
# schon gezeichnet ist – davor stünde der Kasten eine Runde lang leer.
einladung_anzeigen()
offene_einladungen()

st.subheader("Nutzer bearbeiten")
edit_user_data()

st.subheader("Kennwort zurücksetzen")
kennwort_link_formular()
kennwort_link_anzeigen()

st.subheader("Nutzer ausscheiden lassen")
ausscheiden_formular()
ausgeschiedene()
