"""Datumsspalten von VARCHAR(64) auf DATETIME umstellen

Alle Zeitstempel lagen als Text vor, in vier Formaten:

    2024-06-21
    2024-08-05 06:26:57
    2024-08-05 06:26:57.620538
    2024-09-04T11:39:21.716398      (ISO mit T)

Dadurch konnte keine Monatsabfrage einen Index benutzen: EXTRACT(MONTH FROM ts)
auf einer Textspalte zwingt MySQL zum vollständigen Tabellendurchlauf.

Die Umstellung läuft je Spalte in zwei Schritten:

1. Text vereinheitlichen: 'T' durch ein Leerzeichen ersetzen und die
   Sekundenbruchteile abschneiden. Abschneiden, nicht runden -- CAST würde
   06:26:57.620538 zu 06:26:58 aufrunden.
2. ALTER TABLE ... MODIFY auf DATETIME.

Danach werden zusammengesetzte Indizes angelegt, damit die Monatsabfragen
(user_id + Zeitraum) tatsächlich einen Index nutzen können.

Revision ID: b7d41e9c8a02
Revises: a56eccd4707a
Create Date: 2026-09-02 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d41e9c8a02"
down_revision: Union[str, None] = "a56eccd4707a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (Tabelle, Spalte, NULL erlaubt)
DATUMSSPALTEN = [
    ("users", "ts", False),
    ("coffee_log", "ts", False),
    ("payments", "ts", False),
    ("invoices", "monat", False),
    ("invoices", "ts", False),
    ("invoices", "bezahlt", True),
    ("invoices", "email_versand", True),
    ("mietzahlungen", "monat", False),
    ("mietzahlungen", "ts", False),
]

# (Name, Tabelle, Spalten)
INDIZES = [
    # (user_id, ts) für "ein Monat einer Person", (ts) für "ein Monat, alle
    # Personen" -- ein zusammengesetzter Index hilft bei der zweiten Abfrage
    # nicht, weil dort die erste Spalte nicht eingeschränkt wird.
    ("ix_coffee_log_user_ts", "coffee_log", ["user_id", "ts"]),
    ("ix_coffee_log_ts", "coffee_log", ["ts"]),
    ("ix_payments_user_ts", "payments", ["user_id", "ts"]),
    ("ix_payments_ts", "payments", ["ts"]),
    ("ix_invoices_user_monat", "invoices", ["user_id", "monat"]),
    ("ix_invoices_monat", "invoices", ["monat"]),
    ("ix_mietzahlungen_user_monat", "mietzahlungen", ["user_id", "monat"]),
    ("ix_mietzahlungen_monat", "mietzahlungen", ["monat"]),
]


def upgrade() -> None:
    for tabelle, spalte, nullable in DATUMSSPALTEN:
        # Schritt 1: Text vereinheitlichen (NULL bleibt NULL)
        op.execute(
            f"UPDATE `{tabelle}` "
            f"SET `{spalte}` = SUBSTRING_INDEX(REPLACE(`{spalte}`, 'T', ' '), '.', 1) "
            f"WHERE `{spalte}` IS NOT NULL"
        )
        # Schritt 2: Spaltentyp ändern
        op.alter_column(
            tabelle,
            spalte,
            existing_type=sa.String(64),
            type_=sa.DateTime(),
            existing_nullable=nullable,
            nullable=nullable,
        )

    for name, tabelle, spalten in INDIZES:
        op.create_index(name, tabelle, spalten)


def downgrade() -> None:
    for name, tabelle, _ in reversed(INDIZES):
        op.drop_index(name, table_name=tabelle)

    for tabelle, spalte, nullable in reversed(DATUMSSPALTEN):
        op.alter_column(
            tabelle,
            spalte,
            existing_type=sa.DateTime(),
            type_=sa.String(64),
            existing_nullable=nullable,
            nullable=nullable,
        )
