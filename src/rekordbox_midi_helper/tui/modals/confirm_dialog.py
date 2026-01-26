"""
Confirmation Dialog Modal
"""

from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Container, Horizontal


class ConfirmDialog(ModalScreen[bool]):
    """Confirmation dialog modal"""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #message {
        width: 100%;
        height: auto;
        content-align: center middle;
        padding: 2 1;
    }

    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    #buttons > Button {
        margin: 0 1;
    }
    """

    def __init__(self, title: str, message: str = ""):
        super().__init__()
        self.title_text = title
        self.message_text = message

    def compose(self):
        with Container(id="dialog"):
            yield Static(self.title_text, id="title")
            if self.message_text:
                yield Static(self.message_text, id="message")
            with Horizontal(id="buttons"):
                yield Button("Yes", variant="primary", id="btn-yes")
                yield Button("No", variant="default", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)
