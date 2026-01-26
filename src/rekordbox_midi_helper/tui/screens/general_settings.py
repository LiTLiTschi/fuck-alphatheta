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
                yield Static("Loading...", id="midi-output")
                yield Static("Loading...", id="midi-input")
                yield Static("Loading...", id="fps")
                yield Static("Loading...", id="debug-mode")

            with Horizontal(id="actions"):
                yield Button("Edit Settings", variant="primary", id="btn-edit")
                yield Button("Back", variant="default", id="btn-back")

        yield Footer()

    def on_mount(self) -> None:
        """Load and display settings"""
        self.refresh_settings()

    def refresh_settings(self) -> None:
        """Refresh settings display from config"""
        config = self.app.config_service

        # MIDI Output Port
        midi_output = config.get_midi_output_port()
        self.query_one("#midi-output", Static).update(
            f"MIDI Output Port: [cyan]{midi_output}[/]"
        )

        # MIDI Input Port
        midi_input = config.get_midi_input_port()
        if midi_input:
            self.query_one("#midi-input", Static).update(
                f"MIDI Input Port: [cyan]{midi_input}[/]"
            )
        else:
            self.query_one("#midi-input", Static).update(
                "MIDI Input Port: [yellow]Not configured[/]"
            )

        # FPS
        fps = config.get_screen_monitor_fps()
        self.query_one("#fps", Static).update(
            f"Screen Monitor FPS: [cyan]{fps}[/]"
        )

        # Debug Mode
        debug = config.get_debug_mode()
        if debug:
            self.query_one("#debug-mode", Static).update(
                "Debug Mode: [green]Enabled[/]"
            )
        else:
            self.query_one("#debug-mode", Static).update(
                "Debug Mode: [yellow]Disabled[/]"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-edit":
            self.notify("Edit Settings - Coming soon in Phase 5!")
        elif event.button.id == "btn-back":
            self.app.pop_screen()
