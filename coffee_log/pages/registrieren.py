from reflex_test.templates import ThemeState, template
from reflex_test.models.models import *
import reflex as rx
from datetime import datetime

class RegFormState(rx.State):
    form_data: dict = {}
    success: str = ''

    def handle_submit(self, form_data: dict):
        self.form_data = form_data
        self.form_data['admin'] = 0
        self.form_data['mitglied'] = 0
        self.form_data['ts'] = datetime.now()
        try:
            with rx.session() as session:
                session.add(
                    User(
                        **form_data
                    )
                )
                session.commit()
            self.success = 'Erfolg'
        except:
            self.success = 'Fehler'

@template(route="/registrieren", title="Registrierung")
def registrieren() -> rx.Component:
    """Registrierungsformular für neue Nutzer.
    """
    return rx.vstack(
        rx.heading("Registrierung", size="8"),
        rx.card(
            rx.form(
                rx.vstack(
                    rx.input(
                        name='name',
                        placeholder='Vorname und Name',
                        required=True,
                    ),
                    rx.input(
                        name='email',
                        placeholder='E-Mail',
                        required=True,
                    ),
                    rx.input(
                        name='code',
                        placeholder='Kennwort',
                        required=True,
                    ),
                    rx.button(
                        'Registrieren',
                        type='submit',
                    )
                ),
                on_submit=RegFormState.handle_submit,
                reset_on_submit=True,

            )

        ),
        rx.cond(
            RegFormState.success == 'Erfolg',
            rx.chakra.alert(
                rx.chakra.alert_icon(),
                rx.chakra.alert_title(f'Registrierung von {RegFormState.form_data["name"]} war erfolgreich'),
                status='success',
                
            )),
        rx.cond(
            RegFormState.success == 'Fehler',
            rx.chakra.alert(
                rx.chakra.alert_icon(),
                rx.chakra.alert_title('Ein Fehler ist aufgetreten'),
                status='error',
            )
        ),
        rx.text(RegFormState.form_data.to_string())
    )
