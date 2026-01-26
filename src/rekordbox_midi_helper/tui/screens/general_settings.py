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

            # Updates section
            yield Static("", id="updates-spacer")
            yield Static("Updates", id="updates-title")
            with Vertical(id="updates-section"):
                yield Static("Loading...", id="current-version")
                yield Static("Loading...", id="latest-version")
                yield Static("Loading...", id="last-check")

            with Horizontal(id="actions"):
                yield Button("Check for Updates", variant="success", id="btn-check-update")
                yield Button("Edit Settings", variant="primary", id="btn-edit")
                yield Button("Back", variant="default", id="btn-back")

        yield Footer()

    def on_mount(self) -> None:
        """Load and display settings"""
        self.refresh_settings()
        self.refresh_update_info()

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

    def refresh_update_info(self) -> None:
        """Refresh update information display"""
        try:
            from ...utils.update_checker import UpdateChecker
            from ... import __version__
            import time

            checker = UpdateChecker()
            cached_info = checker.get_cached_update_info()

            # Current version
            self.query_one("#current-version", Static).update(
                f"Current Version: [cyan]{__version__}[/]"
            )

            if cached_info:
                # Latest version
                latest = cached_info.get("latest_version", "unknown")
                channel = cached_info.get("channel", "unknown")
                update_available = cached_info.get("update_available", False)

                if update_available:
                    self.query_one("#latest-version", Static).update(
                        f"Latest Version: [green]{latest}[/] ({channel}) - [yellow]Update available![/]"
                    )
                else:
                    self.query_one("#latest-version", Static).update(
                        f"Latest Version: [cyan]{latest}[/] ({channel}) - [green]Up to date[/]"
                    )

                # Last check
                last_check = cached_info.get("last_check_timestamp", 0)
                if last_check:
                    hours_ago = int((time.time() - last_check) / 3600)
                    if hours_ago == 0:
                        time_str = "less than an hour ago"
                    elif hours_ago == 1:
                        time_str = "1 hour ago"
                    else:
                        time_str = f"{hours_ago} hours ago"

                    self.query_one("#last-check", Static).update(
                        f"Last Check: [cyan]{time_str}[/]"
                    )
                else:
                    self.query_one("#last-check", Static).update(
                        "Last Check: [yellow]Never[/]"
                    )
            else:
                self.query_one("#latest-version", Static).update(
                    "Latest Version: [yellow]Not checked yet[/]"
                )
                self.query_one("#last-check", Static).update(
                    "Last Check: [yellow]Never[/]"
                )
        except Exception as e:
            self.query_one("#latest-version", Static).update(
                f"Latest Version: [red]Error: {e}[/]"
            )
            self.query_one("#last-check", Static).update(
                "Last Check: [yellow]Never[/]"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-check-update":
            self.action_check_updates()
        elif event.button.id == "btn-edit":
            self.notify("Edit Settings - Coming soon in Phase 5!")
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def action_check_updates(self) -> None:
        """Check for updates and refresh display"""
        try:
            from ...utils.update_checker import UpdateChecker
            from ... import __version__

            self.notify("Checking for updates...", severity="information")

            checker = UpdateChecker()
            update_info = checker.check_for_updates(
                current_version=__version__,
                channel="dev",  # TODO: Get from config
                force=True
            )

            self.refresh_update_info()

            if update_info.get("update_available"):
                latest = update_info.get("latest_version", "unknown")
                self.notify(f"✓ Update available: {latest}", severity="information")
                self.notify("Run 'fucka update' to upgrade", severity="information")
            else:
                self.notify("✓ You are up to date!", severity="information")

        except Exception as e:
            self.notify(f"✗ Update check failed: {e}", severity="error")
