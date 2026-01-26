"""
Main Menu Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Container, Vertical, Center


class MainMenuScreen(Screen):
    """Main menu with navigation options"""

    BINDINGS = [
        ("q", "app.request_quit", "Quit"),
        ("s", "app.save_config", "Save"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the main menu layout"""
        yield Header()

        with Container(id="main-container"):
            with Center():
                with Vertical(id="menu"):
                    yield Static("Rekordbox MIDI Helper", id="title")
                    yield Static("Configuration Tool v2.0.0", id="subtitle")
                    yield Static("", id="spacer")

                    yield Button("⚙️  General Settings", id="btn-general", variant="primary")
                    yield Button("📺 Screen Monitors", id="btn-monitors", variant="primary")
                    yield Button("⬜ Static Shapes", id="btn-static", variant="primary")
                    yield Button("📊 Animated Shapes", id="btn-animated", variant="primary")
                    yield Button("🧪 Test & Validate", id="btn-test", variant="primary")
                    yield Button("💾 Manage Presets", id="btn-presets", variant="primary")
                    yield Static("", id="spacer2")
                    yield Button("❌ Exit", id="btn-exit", variant="error")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn-general":
            self.notify("General Settings - Coming soon!")
        elif button_id == "btn-monitors":
            self.notify("Screen Monitors - Coming soon!")
        elif button_id == "btn-static":
            self.notify("Static Shapes - Coming soon!")
        elif button_id == "btn-animated":
            self.notify("Animated Shapes - Coming soon!")
        elif button_id == "btn-test":
            self.notify("Test & Validate - Coming soon!")
        elif button_id == "btn-presets":
            self.notify("Manage Presets - Coming soon!")
        elif button_id == "btn-exit":
            self.app.action_request_quit()
