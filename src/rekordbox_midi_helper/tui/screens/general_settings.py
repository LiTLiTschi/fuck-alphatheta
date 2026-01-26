"""
General Settings Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Container, Vertical, Horizontal


class GeneralSettingsScreen(Screen):
    """General settings configuration screen"""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("b", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the settings layout"""
        yield Header()

        with Container(id="settings-container"):
            yield Static("General Settings", id="screen-title")

            with Vertical(id="settings-list"):
                yield Static("MIDI Output Port: [cyan]Not configured[/]", id="midi-output")
                yield Static("MIDI Input Port: [cyan]Not configured[/]", id="midi-input")
                yield Static("Screen Monitor FPS: [cyan]30[/]", id="fps")
                yield Static("Debug Mode: [yellow]Disabled[/]", id="debug-mode")

            with Horizontal(id="actions"):
                yield Button("Edit Settings", variant="primary", id="btn-edit")
                yield Button("Back", variant="default", id="btn-back")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-edit":
            self.notify("Edit Settings - Coming soon!")
        elif event.button.id == "btn-back":
            self.app.pop_screen()
