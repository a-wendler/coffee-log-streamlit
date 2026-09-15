"""Alle Daten der App als Excel-Mappe.

Bewusst ohne Streamlit: Die Funktion bekommt Daten herein und gibt Bytes
zurück. Damit lässt sie sich ohne laufende App testen.

Geschrieben wird mit openpyxl statt über pandas, weil die Beträge als
``Decimal`` aus der Datenbank kommen. openpyxl schreibt die direkt als Zahl
in die Zelle; pandas würde die Spalte zum Objekt-Typ machen und die Beträge
wären in Excel Text, mit dem sich nicht rechnen lässt.

Die Mappe hat drei Blätter:

* **Kaffees** – jeder Logbucheintrag, mit Namen statt User-ID.
* **Zahlungen** – jede Buchung, ebenfalls mit Namen.
* **Kontoübersicht** – je Konto der Saldo, die offenen Rechnungen und die
  Kaffees, die noch in keiner Rechnung stehen.
"""

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# Zahlenformate. Excel zeigt sie mit den Trennzeichen der eingestellten
# Sprache an, in einer deutschen Installation also mit Komma.
EURO = '#,##0.00 €'
DATUM = "DD.MM.YYYY"
DATUM_ZEIT = "DD.MM.YYYY HH:MM"
GANZZAHL = "0"

KOPFZEILE = Font(bold=True)


class Spalte:
    """Eine Spalte eines Blattes: Überschrift, Wert, Breite, Format."""

    def __init__(self, ueberschrift, wert, breite=14, format=None):
        self.ueberschrift = ueberschrift
        self.wert = wert
        self.breite = breite
        self.format = format


def _ja_nein(wert) -> str:
    return "ja" if wert else "nein"


KAFFEE_SPALTEN = [
    Spalte("Datum", lambda z: z.ts, 18, DATUM_ZEIT),
    Spalte("Name", lambda z: z.name, 18),
    Spalte("Vorname", lambda z: z.vorname, 18),
    Spalte("Anzahl", lambda z: z.anzahl, 10, GANZZAHL),
    Spalte("abgerechnet", lambda z: _ja_nein(z.abgerechnet), 14),
]

ZAHLUNGS_SPALTEN = [
    Spalte("Datum", lambda z: z.ts, 18, DATUM_ZEIT),
    Spalte("Name", lambda z: z.name, 18),
    Spalte("Vorname", lambda z: z.vorname, 18),
    Spalte("Art", lambda z: z.typ, 14),
    Spalte("Betrag", lambda z: z.betrag, 14, EURO),
    Spalte("Betreff", lambda z: z.betreff, 40),
    Spalte("Rechnung", lambda z: z.invoice_id, 12, GANZZAHL),
]

KONTO_SPALTEN = [
    Spalte("Name", lambda z: z.name, 18),
    Spalte("Vorname", lambda z: z.vorname, 18),
    Spalte("Mitglied", lambda z: _ja_nein(z.mitglied), 12),
    Spalte("Status", lambda z: z.status or "", 12),
    Spalte("Saldo", lambda z: z.saldo, 14, EURO),
    Spalte("offene Rechnungen", lambda z: z.offene_rechnungen, 18, GANZZAHL),
    Spalte("offener Betrag", lambda z: z.offener_betrag, 16, EURO),
    Spalte("nicht abgerechnete Kaffees", lambda z: z.unabgerechnete_kaffees, 26,
           GANZZAHL),
]


def _blatt(mappe: Workbook, titel: str, spalten, zeilen):
    """Ein Blatt mit fixierter Kopfzeile und Filter über allen Spalten."""
    blatt = mappe.create_sheet(titel)

    for nummer, spalte in enumerate(spalten, start=1):
        zelle = blatt.cell(row=1, column=nummer, value=spalte.ueberschrift)
        zelle.font = KOPFZEILE
        zelle.alignment = Alignment(vertical="top", wrap_text=True)
        blatt.column_dimensions[get_column_letter(nummer)].width = spalte.breite

    for zeilennummer, daten in enumerate(zeilen, start=2):
        for nummer, spalte in enumerate(spalten, start=1):
            zelle = blatt.cell(row=zeilennummer, column=nummer, value=spalte.wert(daten))
            if spalte.format:
                zelle.number_format = spalte.format

    # Kopfzeile stehen lassen und sortierbar machen: Die Kaffee- und
    # Zahlungsblätter werden über die Jahre lang, und wer sie öffnet, sucht
    # meistens nach einer Person.
    blatt.freeze_panes = "A2"
    blatt.auto_filter.ref = (
        f"A1:{get_column_letter(len(spalten))}{max(len(zeilen), 1) + 1}"
    )
    return blatt


def export_als_excel(daten) -> bytes:
    """Baut die Mappe und gibt sie als Bytes zurück.

    ``daten`` ist ein ``database.queries.Exportdaten``.
    """
    mappe = Workbook()
    # Workbook() legt ein leeres Blatt an, das hier nicht gebraucht wird.
    mappe.remove(mappe.active)

    _blatt(mappe, "Kaffees", KAFFEE_SPALTEN, daten.kaffees)
    _blatt(mappe, "Zahlungen", ZAHLUNGS_SPALTEN, daten.zahlungen)
    _blatt(mappe, "Kontoübersicht", KONTO_SPALTEN, daten.konten)

    puffer = BytesIO()
    mappe.save(puffer)
    return puffer.getvalue()


def dateiname(erstellt) -> str:
    """Dateiname des Exports, z. B. Kaffeeabrechnung-Export-2026-09-15.xlsx."""
    return f"Kaffeeabrechnung-Export-{erstellt:%Y-%m-%d}.xlsx"
