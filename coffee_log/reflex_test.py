"""Welcome to Reflex!."""

# Import all the pages.
from coffee_log.pages import *
from coffee_log.models import models

import reflex as rx


class State(rx.State):
    """Define empty state to allow access to rx.State.router."""


# Create the app.
app = rx.App()
