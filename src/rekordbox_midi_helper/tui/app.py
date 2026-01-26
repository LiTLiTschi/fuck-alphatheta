"""
Main Textual Application for Rekordbox MIDI Helper
"""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from .screens import (
    MainMenuScreen,
    GeneralSettingsScreen,
    MonitorsScreen,
    StaticShapesScreen,
    AnimatedShapesScreen,
    TestValidateScreen,
    PresetsScreen,
)


class RekordboxConfigApp(App):
    """Rekordbox MIDI Helper Configuration TUI"""

    TITLE = "Rekordbox MIDI Helper"
    SUB_TITLE = "v2.1.0 - Modern Configuration Interface"

    CSS_PATH = "styles/main.tcss"

    BINDINGS = [
        Binding("q", "request_quit", "Quit", show=True, priority=True),
        Binding("s", "save_config", "Save", show=True),
        ("ctrl+c", "request_quit", "Quit"),
        ("?", "show_help", "Help"),
    ]

    SCREENS = {
        "main_menu": MainMenuScreen,
        "general_settings": GeneralSettingsScreen,
        "monitors": MonitorsScreen,
        "static_shapes": StaticShapesScreen,
        "animated_shapes": AnimatedShapesScreen,
        "test_validate": TestValidateScreen,
        "presets": PresetsScreen,
    }

    def __init__(self, config_path: str = None):
        super().__init__()
        self.config_path = config_path

        # Initialize config service
        from ..services import ConfigService
        self.config_service = ConfigService(config_path)

    def on_mount(self) -> None:
        """Initialize app on mount"""
        self.push_screen("main_menu")

    def action_save_config(self) -> None:
        """Save configuration"""
        try:
            self.config_service.save()
            self.notify("✓ Configuration saved", severity="information")
        except Exception as e:
            self.notify(f"✗ Save failed: {e}", severity="error")

    async def action_request_quit(self) -> None:
        """Quit with unsaved changes check"""
        if self.config_service.has_unsaved_changes():
            from .modals.confirm_dialog import ConfirmDialog

            confirmed = await self.push_screen_wait(
                ConfirmDialog(
                    "Quit without saving?",
                    "You have unsaved changes that will be lost."
                )
            )

            if not confirmed:
                return

        self.exit()

    def action_show_help(self) -> None:
        """Show help screen"""
        self.notify("Help: Press 'q' to quit, 's' to save", severity="information")
