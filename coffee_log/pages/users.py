"""Nutzerverwaltung."""
import reflex as rx
from sqlalchemy import select
from coffee_log.templates import template
from coffee_log.models.models import User, CoffeeLog

class UserState(rx.State):
    """The app state."""

    id: int
    name: str = ""
    email: str = ""
    admin: int
    mitglied: int
    users: list[User] = []
    num_customers: int

    def load_entries(self) -> list[User]:
        """Get all users from the database."""
        with rx.session() as session:
            self.users = session.exec(select(User)).all()
            self.num_customers = len(self.users)

    def set_user_vars(self, user: User):
        print(user)
        self.id = user["id"]
        self.name = user["name"]
        self.email = user["email"]
        self.admin = user["admin"]
        self.mitglied = user["mitglied"]

    def add_customer(self):
        """Add a customer to the database."""
        with rx.session() as session:
            if session.exec(
                select(User).where(User.email == self.email)
            ).first():
                return rx.window_alert("Nutzer/-in existiert bereits.")
            session.add(
                User(
                    name=self.name,
                    email=self.email,
                )
            )
            session.commit()
        self.load_entries()
        return rx.window_alert(f"Nutzer/-in {self.name} wurde hinzugefügt.")

    def update_customer(self):
        """Update a customer in the database."""
        with rx.session() as session:
            customer = session.exec(
                select(User).where(User.id == self.id)
            ).first()
            customer.name = self.name
            customer.email = self.email
            print(customer)
            session.add(customer)
            session.commit()
        self.load_entries()

    def delete_customer(self, email: str):
        """Delete a customer from the database."""
        with rx.session() as session:
            customer = session.exec(
                select(User).where(User.email == email)
            ).first()
            session.delete(customer)
            session.commit()
        self.load_entries()

    def on_load(self):
        self.load_entries()


def show_customer(user: User):
    """Show a customer in a table row."""
    return rx.table.row(
        rx.table.cell(user.name),
        rx.table.cell(user.email),
        rx.table.cell(
            update_customer(user),
        ),
        rx.table.cell(
            rx.button(
                "Löschen",
                on_click=lambda: UserState.delete_customer(user.email),
                bg="red",
                color="white",
            ),
        ),
    )


def add_customer():
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.flex(
                    "Nutzer/-in hinzufügen",
                    rx.icon(tag="plus", width=24, height=24),
                    spacing="3",
                ),
                size="4",
                radius="full",
            ),
        ),
        rx.dialog.content(
            rx.dialog.title(
                "Details",
                font_family="Inter",
            ),
            rx.dialog.description(
                "Add your customer profile details.",
                size="2",
                mb="4",
                padding_bottom="1em",
            ),
            rx.flex(
                rx.text(
                    "Name",
                    as_="div",
                    size="2",
                    mb="1",
                    weight="bold",
                ),
                rx.input(placeholder="Name", on_blur=UserState.set_name),
                rx.text(
                    "Email",
                    as_="div",
                    size="2",
                    mb="1",
                    weight="bold",
                ),
                rx.input(placeholder="E-Mail", on_blur=UserState.set_email),
                direction="column",
                spacing="3",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Abbrechen",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Speichern  ",
                        on_click=UserState.add_customer,
                        variant="solid",
                    ),
                ),
                padding_top="1em",
                spacing="3",
                mt="4",
                justify="end",
            ),
            style={"max_width": 450},
            box_shadow="lg",
            padding="1em",
            border_radius="25px",
            font_family="Inter",
        ),
    )


def update_customer(user):
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.icon("square_pen", width=24, height=24),
                bg="red",
                color="white",
                on_click=lambda: UserState.set_user_vars(user),
            ),
        ),
        rx.dialog.content(
            rx.dialog.title("Customer Details"),
            rx.dialog.description(
                "Update your customer profile details.",
                size="2",
                mb="4",
                padding_bottom="1em",
            ),
            rx.flex(
                rx.text(
                    "Name",
                    as_="div",
                    size="2",
                    mb="1",
                    weight="bold",
                ),
                rx.input(
                    placeholder=user.name,
                    default_value=user.name,
                    on_blur=UserState.set_name,
                ),
                rx.text(
                    "Email",
                    as_="div",
                    size="2",
                    mb="1",
                    weight="bold",
                ),
                rx.input(
                    placeholder=user.email,
                    default_value=user.email,
                    on_blur=UserState.set_email,
                ),
                ),
                direction="column",
                spacing="3",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Cancel",
                        variant="soft",
                        color_scheme="gray",
                    ),
                ),
                rx.dialog.close(
                    rx.button(
                        "Submit Customer",
                        on_click=UserState.update_customer,
                        variant="solid",
                    ),
                ),
                padding_top="1em",
                spacing="3",
                mt="4",
                justify="end",
            ),
            style={"max_width": 450},
            box_shadow="lg",
            padding="1em",
            border_radius="25px",
        )


def navbar():
    return rx.hstack(
        rx.vstack(
            rx.heading("Nutzerverwaltung", size="7", font_family="Inter"),
        ),
        rx.spacer(),
        add_customer(),
        rx.avatar(fallback="TG", size="4"),
        rx.color_mode.button(rx.color_mode.icon(), size="3", float="right"),
        position="fixed",
        width="100%",
        top="0px",
        z_index="1000",
        padding_x="4em",
        padding_top="2em",
        padding_bottom="1em",
        backdrop_filter="blur(10px)",
    )


def content():
    return rx.fragment(
        rx.vstack(
            rx.divider(),
            rx.hstack(
                rx.heading(
                    f"{UserState.num_customers} Nutzende",
                    size="5",
                    font_family="Inter",
                ),
                rx.spacer(),
                width="100%",
                padding_x="2em",
                padding_top="2em",
                padding_bottom="1em",
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Name"),
                        rx.table.column_header_cell("Email"),
                        rx.table.column_header_cell("Bearbeiten"),
                        rx.table.column_header_cell("Löschen"),
                    ),
                ),
                rx.table.body(rx.foreach(UserState.users, show_customer)),
                # variant="surface",
                size="3",
                width="100%",
            ),
        ),
    )

@template(route="/users", title="Nutzerverwaltung")
def users() -> rx.Component:
    """Nutzerverwaltung.

    Returns:
        The UI for the dashboard page.
    """
    return rx.box(
        navbar(),
        rx.box(
            content(),
            margin_top="calc(50px + 2em)",
            padding="4em",
        ),
        on_mount=UserState.on_load,
    )
