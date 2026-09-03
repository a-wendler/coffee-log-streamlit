import re
from datetime import datetime
from decimal import Decimal


def get_first_days_of_last_six_months():
    # Get the current date
    current_date = datetime.now()

    # Initialize an empty list to store the first days
    first_days = []

    # Loop to get the first day of the last 6 months including the current month
    for i in range(6):
        # Calculate the month and year
        month = (current_date.month - i - 1) % 12 + 1
        year = current_date.year + (current_date.month - i - 1) // 12

        # Get the first day of the month
        first_day = datetime(year, month, 1)

        # Append the first day to the list
        first_days.append(first_day)

    return first_days


def monatsbereich(datum):
    """Erster Tag des Monats und erster Tag des Folgemonats.

    Für Abfragen als ``ts >= start`` und ``ts < ende``. Das nutzt einen Index,
    während ``EXTRACT(MONTH FROM ts) == …`` die Spalte in eine Funktion steckt
    und MySQL deshalb jede Zeile lesen muss.
    """
    start = datetime(datum.year, datum.month, 1)
    if datum.month == 12:
        ende = datetime(datum.year + 1, 1, 1)
    else:
        ende = datetime(datum.year, datum.month + 1, 1)
    return start, ende


def euro(betrag) -> str:
    """Formatiert einen Betrag als € mit deutschem Dezimalkomma."""
    return "€ " + f"{Decimal(betrag):.2f}".replace(".", ",")


def is_valid_email(email) -> bool:
    """Grobe Plausibilitätsprüfung einer E-Mail-Adresse."""
    return re.match(r"^[\+\w\.-]+@[\w\.-]+\.\w+$", email) is not None


# Streamlit liefert englische Monatsnamen; die Oberfläche ist deutsch.
MONATSNAMEN = {
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
    """Monat und Jahr auf Deutsch, z. B. „März 2026“."""
    return MONATSNAMEN[datum.strftime("%B")] + " " + datum.strftime("%Y")
