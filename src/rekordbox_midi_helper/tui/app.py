"""
Main Textual Application for Rekordbox MIDI Helper
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from .screens.main_menu import MainMenuScreen


class RekordboxConfigApp(App):
    """Rekordbox MIDI Helper Configuration TUI"""

    TITLE = "Rekordbox MIDI Helper"
    SUB_TITLE = "v2.0.0 - Modern Configuration Interface"

    CSS_PATH = "styles/main.tcss"

    BINDINGS = [
        Binding("q", "request_quit", "Quit", show=True, priority=True),
        Binding("s", "save_config", "Save", show=True),
        ("ctrl+c", "request_quit", "Quit"),
        ("?", "show_help", "Help"),
    ]

    SCREENS = {
        "main_menu": MainMenuScreen,
    }

    def __init__(self, config_path: str = None):
        super().__init__()
        self.config_path = config_path
        self.unsaved_changes = False

    def on_mount(self) -> None:
        """Initialize app on mount"""
        self.push_screen("main_menu")

    def action_save_config(self) -> None:
        """Save configuration"""
        try:
            # TODO: Implement save logic
            self.unsaved_changes = False
            self.notify("✓ Configuration saved", severity="information")
        except Exception as e:
            self.notify(f"✗ Save failed: {e}", severity="error")

    def action_request_quit(self) -> None:
        """Quit with unsaved changes check"""
        if self.unsaved_changes:
            # TODO: Show confirmation dialog
            pass

        self.exit()

    def action_show_help(self) -> None:
        """Show help screen"""
        self.notify("Help: Press 'q' to quit, 's' to save", severity="information")
