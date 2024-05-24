import reflex as rx
import sqlmodel
from datetime import datetime

class User(rx.Model, table=True):
    name: str
    email: str
    code: str
    admin: int
    mitglied: int
    ts: datetime

class CoffeeLog(rx.Model, table=True):
    user_id: int = sqlmodel.Field(foreign_key="user.id")
    anzahl: int
    ts: datetime

class Payments(rx.Model, table=True):
    user_id: int = sqlmodel.Field(foreign_key="user.id")
    betrag: float
    betreff: str
    ts: datetime
