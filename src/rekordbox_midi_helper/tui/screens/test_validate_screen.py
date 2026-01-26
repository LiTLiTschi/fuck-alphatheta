"""
Test & Validate Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static
from textual.containers import Container, Vertical


class TestValidateScreen(Screen):
    """Test and validation tools screen"""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("b", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the test layout"""
        yield Header()

        with Container(id="test-container"):
            yield Static("Test & Validate", id="screen-title")

            with Vertical(id="test-options"):
                yield Button("🎹 Test MIDI Connections", variant="primary", id="btn-test-midi")
                yield Button("✓ Validate Configuration", variant="primary", id="btn-validate")
                yield Button("👁️ Live Preview Monitors", variant="primary", id="btn-preview")
                yield Button("🔍 Debug Shapes (Test Overlay)", variant="primary", id="btn-debug")
                yield Static("", id="spacer")
                yield Button("Back", variant="default", id="btn-back")

        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-test-midi":
            self.notify("Test MIDI Connections - Coming soon!")
        elif event.button.id == "btn-validate":
            self.notify("Validate Configuration - Coming soon!")
        elif event.button.id == "btn-preview":
            self.notify("Live Preview - Coming soon!")
        elif event.button.id == "btn-debug":
            self.notify("Debug Shapes - Coming soon!")
        elif event.button.id == "btn-back":
            self.app.pop_screen()
