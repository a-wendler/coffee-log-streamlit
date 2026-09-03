"""Rechnung als PDF.

Bewusst ohne Streamlit: Die Funktion bekommt Daten und Kontaktadressen
herein und gibt Bytes zurück. Damit lässt sie sich ohne laufende App testen.

Zur Schrift: fpdf2 kodiert die eingebauten Schriften standardmäßig als
Latin-1, und darin fehlt das Eurozeichen. Mit ``core_fonts_encoding =
"cp1252"`` landet es als Byte 0x80 im Dokument, und weil fpdf2 für die
Standardschriften ohnehin WinAnsiEncoding deklariert, zeigt jeder Betrachter
es richtig an. So muss keine Schriftdatei mitgeliefert werden.
"""

from decimal import Decimal

from fpdf import FPDF

from helpers import euro, monatsname

RAND = 20
BREITE = 210 - 2 * RAND  # A4 abzüglich der Ränder
GRAU = (110, 110, 110)
SCHWARZ = (0, 0, 0)


def _datum(wert) -> str:
    return wert.strftime("%d.%m.%Y") if wert else "–"


class Rechnung(FPDF):
    """PDF mit Fußzeile auf jeder Seite."""

    def __init__(self, fusszeile: str):
        super().__init__(format="A4")
        self.fusszeile = fusszeile
        self.core_fonts_encoding = "cp1252"
        self.set_margins(RAND, RAND, RAND)
        self.set_auto_page_break(True, margin=25)

    def footer(self):
        self.set_y(-20)
        self.set_font("helvetica", size=8)
        self.set_text_color(*GRAU)
        self.multi_cell(BREITE, 4, self.fusszeile, align="C")
        self.set_text_color(*SCHWARZ)


def _abschnitt(pdf: Rechnung, titel: str):
    pdf.ln(4)
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(BREITE, 7, titel, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 200, 200)
    pdf.line(RAND, pdf.get_y(), RAND + BREITE, pdf.get_y())
    pdf.ln(2)


def _zeile(pdf: Rechnung, bezeichnung: str, wert: str, fett: bool = False):
    """Beschriftung links, Betrag rechtsbündig - so stehen die Kommas unter sich."""
    pdf.set_font("helvetica", "B" if fett else "", 10)
    pdf.cell(BREITE - 40, 6, bezeichnung)
    pdf.cell(40, 6, wert, align="R", new_x="LMARGIN", new_y="NEXT")


def rechnung_als_pdf(daten, zahlungsoptionen: str, kontakt_rechnung: str,
                     kontakt_technik: str) -> bytes:
    """Baut die PDF-Rechnung und gibt sie als Bytes zurück.

    ``daten`` ist ein ``database.queries.Rechnungsdaten``.
    """
    pdf = Rechnung(
        f"Fragen zur Abrechnung: {kontakt_rechnung} | "
        f"Technische Fragen: {kontakt_technik}"
    )
    pdf.add_page()

    # --- Kopf ---
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(BREITE, 9, "LSB Kaffeeabrechnung", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 13)
    pdf.set_text_color(*GRAU)
    pdf.cell(
        BREITE,
        7,
        f"Rechnung für {monatsname(daten.monat)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(*SCHWARZ)
    pdf.ln(4)

    pdf.set_font("helvetica", "", 10)
    pdf.cell(BREITE, 6, f"{daten.vorname} {daten.name}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(*GRAU)
    pdf.cell(BREITE, 5, daten.email, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        BREITE,
        5,
        f"Rechnungsnummer {daten.invoice_id} · erstellt am {_datum(daten.erstellt)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_text_color(*SCHWARZ)

    # --- Kaffee ---
    _abschnitt(pdf, "Kaffee")
    _zeile(pdf, "Getrunkene Tassen", str(daten.kaffee_anzahl))
    _zeile(pdf, "Preis je Tasse", euro(daten.preis_je_tasse))
    _zeile(pdf, "Kaffeekosten", euro(daten.kaffee_preis), fett=True)

    # --- Zahlungen des Monats ---
    _abschnitt(pdf, "Ihre Buchungen in diesem Monat")
    if daten.zahlungen:
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*GRAU)
        pdf.cell(25, 6, "Datum")
        pdf.cell(28, 6, "Art")
        pdf.cell(BREITE - 25 - 28 - 30, 6, "Betreff")
        pdf.cell(30, 6, "Betrag", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*SCHWARZ)
        pdf.set_font("helvetica", "", 9)
        for zahlung in daten.zahlungen:
            pdf.cell(25, 6, _datum(zahlung["ts"]))
            pdf.cell(28, 6, zahlung["typ"])
            pdf.cell(BREITE - 25 - 28 - 30, 6, zahlung["betreff"][:48])
            pdf.cell(
                30, 6, euro(zahlung["betrag"]), align="R",
                new_x="LMARGIN", new_y="NEXT",
            )
        _zeile(pdf, "Summe", euro(daten.zahlungen_summe), fett=True)
    else:
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(*GRAU)
        pdf.cell(
            BREITE,
            6,
            "In diesem Monat wurde nichts für Sie gebucht.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_text_color(*SCHWARZ)

    # --- Rechnung ---
    _abschnitt(pdf, "Abrechnung")
    # Zwei Zeilen, eine Subtraktion: Das kann jede Person nachrechnen. Die
    # Buchungen von oben stecken schon im Saldo davor, sonst stünden sie
    # doppelt in der Rechnung.
    _zeile(
        pdf,
        "Saldo vor dieser Rechnung (mit den Buchungen oben)",
        euro(daten.saldo_vorher),
    )
    _zeile(pdf, "Kaffeekosten", euro(-daten.kaffee_preis))
    _zeile(pdf, "Saldo nach dieser Rechnung", euro(daten.saldo_nachher), fett=True)

    if daten.angerechnetes_guthaben > 0:
        pdf.ln(2)
        _zeile(
            pdf,
            "davon mit vorhandenem Guthaben verrechnet",
            euro(daten.angerechnetes_guthaben),
        )

    pdf.ln(3)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(BREITE - 40, 8, "Zu zahlen")
    pdf.cell(40, 8, euro(daten.zahlbetrag), align="R", new_x="LMARGIN", new_y="NEXT")

    # --- Status ---
    pdf.ln(4)
    if daten.bezahlt:
        text = (
            f"Diese Rechnung ist bezahlt. Der Zahlungseingang wurde am "
            f"{_datum(daten.bezahlt)} verbucht."
        )
    elif daten.zahlbetrag <= 0:
        text = (
            "Es ist keine Zahlung nötig. Die Kaffeekosten wurden vollständig "
            "mit Ihrem Guthaben verrechnet."
        )
    else:
        text = f"Bitte überweisen Sie {euro(daten.zahlbetrag)}.\n\n{zahlungsoptionen}"

    pdf.set_font("helvetica", "", 10)
    pdf.set_fill_color(242, 242, 242)
    pdf.multi_cell(BREITE, 6, text, fill=True, border=0)

    pdf.ln(4)
    pdf.set_font("helvetica", "", 8)
    pdf.set_text_color(*GRAU)
    pdf.multi_cell(
        BREITE,
        4,
        "Ein negativer Saldo bedeutet, dass noch etwas offen ist, ein positiver "
        "ist Ihr Guthaben. Kaffees des laufenden Monats sind noch nicht "
        "abgerechnet und deshalb hier nicht enthalten.",
    )

    return bytes(pdf.output())


def dateiname(monat, name: str) -> str:
    """Dateiname der Rechnung, z. B. Kaffeerechnung-2026-08-Bohne.pdf.

    Nimmt Monat und Nachnamen einzeln entgegen, nicht die ganzen
    Rechnungsdaten: Der Name steht schon beim Aufbau der Seite fest, die
    übrigen Daten werden erst beim Klick geladen.
    """
    sauber = "".join(z for z in name if z.isalnum()) or "Rechnung"
    return f"Kaffeerechnung-{monat:%Y-%m}-{sauber}.pdf"
