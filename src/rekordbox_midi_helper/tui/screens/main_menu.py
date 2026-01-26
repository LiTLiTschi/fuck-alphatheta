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
            # Update notification banner (initially hidden)
            yield Static("", id="update-banner", classes="hidden")

            with Center():
                with Vertical(id="menu"):
                    yield Static("Rekordbox MIDI Helper", id="title")
                    yield Static("Configuration Tool v2.1.0", id="subtitle")
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

    def on_mount(self) -> None:
        """Check for updates when screen is mounted"""
        self._check_for_updates()

    def _check_for_updates(self) -> None:
        """Check for updates and display banner if available"""
        try:
            from ...utils.update_checker import UpdateChecker
            from ... import __version__

            checker = UpdateChecker()
            cached_info = checker.get_cached_update_info()

            if not cached_info:
                return  # No cached info

            if checker.is_cache_expired(cached_info):
                return  # Cache expired

            if not cached_info.get("update_available"):
                return  # No update available

            # Show update notification
            latest = cached_info.get("latest_version", "unknown")
            channel = cached_info.get("channel", "unknown")

            banner = self.query_one("#update-banner", Static)
            banner.update(f"🔔 Update available: {latest} ({channel}) - Run 'fucka update' to upgrade")
            banner.remove_class("hidden")
            banner.add_class("update-available")
        except Exception:
            # Silently fail
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn-general":
            self.app.push_screen("general_settings")
        elif button_id == "btn-monitors":
            self.app.push_screen("monitors")
        elif button_id == "btn-static":
            self.app.push_screen("static_shapes")
        elif button_id == "btn-animated":
            self.app.push_screen("animated_shapes")
        elif button_id == "btn-test":
            self.app.push_screen("test_validate")
        elif button_id == "btn-presets":
            self.app.push_screen("presets")
        elif button_id == "btn-exit":
            self.app.action_request_quit()
