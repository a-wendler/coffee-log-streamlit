"""Welcome to Reflex!."""

# Import all the pages.
from reflex_test.pages import *
from reflex_test.models import models

import reflex as rx


class State(rx.State):
    """Define empty state to allow access to rx.State.router."""


# Create the app.
app = rx.App()
