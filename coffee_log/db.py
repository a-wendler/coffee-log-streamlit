"""Zentrale Datenbankverbindung.

Alle Seiten holen ihre Verbindung über ``get_connection()``. Streamlit cacht
``st.connection`` anhand *aller* Argumente – nur wenn der Aufruf überall
identisch ist, teilen sich die Seiten einen einzigen Connection-Pool.

Die Zugangsdaten kommen aus ``.streamlit/secrets.toml``
(Abschnitt ``[connections.coffee_counter]``); eine URL muss nicht gebaut werden.
"""

import streamlit as st
from sqlalchemy.pool import QueuePool


def get_connection():
    """Liefert die gemeinsam genutzte SQL-Verbindung."""
    return st.connection(
        "coffee_counter",
        type="sql",
        pool_size=5,  # dauerhaft vorgehaltene Verbindungen
        max_overflow=10,  # zusätzlich erlaubte Verbindungen
        pool_timeout=30,  # Sekunden bis zum Timeout
        pool_recycle=1800,  # Verbindungen nach 30 Minuten erneuern
        pool_pre_ping=True,  # Verbindung vor Benutzung prüfen
        poolclass=QueuePool,
    )
