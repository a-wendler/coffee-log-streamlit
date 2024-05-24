"""The dashboard page."""
import reflex as rx
from sqlalchemy import select
from reflex_test.templates import template
from reflex_test.models.models import *

class DashboardFormState(rx.State):
    form_data: dict = {}
    user = ''

    def handle_submit(self, form_data: dict):
        self.form_data = form_data
        
        
        with rx.session() as session:            
            user = session.exec(
                select(User).where(User.code == self.form_data['code'])
            ).scalar_one_or_none()
            session.commit()
            self.user = user.id


@template(route="/dashboard", title="Dashboard")
def dashboard() -> rx.Component:
    """The dashboard page.

    Returns:
        The UI for the dashboard page.
    """
    return rx.vstack(
        rx.heading("Dashboard", size="8"),
        rx.text("Welcome to Reflex!"),
        rx.text(
            "You can edit this page in ",
            rx.code("{your_app}/pages/dashboard.py"),
        ),
        rx.form(
            rx.vstack(
                rx.input(
                    name='code',
                    placeholder='Ihr Kennwort',
                ),
                rx.button(f'Kaffee eintragen', type='submit'),
            ),
            on_submit=DashboardFormState.handle_submit,
        ),
        rx.text(DashboardFormState.user)
    )
