"""The dashboard page."""
import reflex as rx
from sqlalchemy import select
from coffee_log.templates import template
from coffee_log.models.models import User, CoffeeLog

class UserTable(rx.State):
    users:list = []

    def load_data(self):
        with rx.session() as session:
            result = session.exec(select(User.name, User.admin, User.mitglied)).all()
            for row in result:
                self.users.append([row.name, bool(row.admin), bool(row.mitglied)])

    def get_edited_data(self, pos, val) -> str:
        col, row = pos
        self.users[row][col] = val["data"]

    # def update_user(self, user):


@template(route="/dashboard", title="Dashboard")
def dashboard() -> rx.Component:
    """The dashboard page.

    Returns:
        The UI for the dashboard page.
    """
    return rx.vstack(
        rx.heading("Dashboard", size="8"),
        rx.data_editor(
            data=UserTable.users,
            columns=[
                {"title":"Name", "type":"str"},
                {"title":"Admin", "type":"bool"},
                {"title":"Mitglied", "type":"bool"},
            ],
            pagination=True,
            search=True,
            sort=True,
            on_cell_edited=UserTable.get_edited_data,
        ),
        on_mount=UserTable.load_data,
    )
