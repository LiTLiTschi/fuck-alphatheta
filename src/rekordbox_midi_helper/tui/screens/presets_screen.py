"""
Presets Management Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Button, Static
from textual.containers import Container, Horizontal


class PresetsScreen(Screen):
    """Presets management screen"""

    BINDINGS = [
        ("n", "new", "New"),
        ("s", "switch", "Switch"),
        ("escape", "app.pop_screen", "Back"),
        ("b", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the presets layout"""
        yield Header()

        with Container(id="presets-container"):
            yield Static("Manage Presets", id="screen-title")
            yield Static("Active: [cyan]default[/]", id="active-preset")
            yield DataTable(id="presets-table")

            with Horizontal(id="actions"):
                yield Button("Switch", variant="primary", id="btn-switch")
                yield Button("New", variant="success", id="btn-new")
                yield Button("Copy", variant="default", id="btn-copy")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Back", variant="default", id="btn-back")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize table with data"""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Add columns
        table.add_columns("Name", "Monitors", "Static", "Animated", "Status")

        # Load actual data
        self.refresh_display()

    def refresh_display(self) -> None:
        """Refresh preset display"""
        # Update active preset label
        active_preset = self.app.config_service.get_active_preset_name()
        self.query_one("#active-preset", Static).update(
            f"Active: [cyan]{active_preset}[/]"
        )

        # Refresh table
        table = self.query_one(DataTable)
        table.clear()

        preset_names = self.app.config_service.get_preset_names()

        for preset_name in preset_names:
            preset = self.app.config_service.get_preset(preset_name)

            # Count items
            monitors = len(preset.get('screen_monitors', []))
            static = len(preset.get('shapes', {}).get('static', []))
            animated = len(preset.get('shapes', {}).get('animated', []))

            # Status
            if preset_name == active_preset:
                status = "[green]● Active[/]"
            else:
                status = ""

            table.add_row(preset_name, str(monitors), str(static), str(animated), status, key=preset_name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-switch":
            self.action_switch()
        elif event.button.id == "btn-new":
            self.action_new()
        elif event.button.id == "btn-copy":
            self.action_copy()
        elif event.button.id == "btn-delete":
            self.action_delete()
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def action_switch(self) -> None:
        """Switch active preset"""
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            preset_name = table.get_row_at(table.cursor_row)[0]
            if preset_name:
                try:
                    self.app.config_service.switch_preset(preset_name)
                    self.refresh_display()
                    self.notify(f"✓ Switched to preset '{preset_name}'")
                except ValueError as e:
                    self.notify(f"✗ {str(e)}", severity="error")

    def action_new(self) -> None:
        """Create new preset"""
        self.notify("New Preset - Coming in Phase 5!")

    def action_copy(self) -> None:
        """Copy preset"""
        self.notify("Copy Preset - Coming in Phase 5!")

    def action_delete(self) -> None:
        """Delete preset"""
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            preset_name = table.get_row_at(table.cursor_row)[0]
            if preset_name:
                try:
                    self.app.config_service.delete_preset(preset_name)
                    self.refresh_display()
                    self.notify(f"✓ Deleted preset '{preset_name}'")
                except ValueError as e:
                    self.notify(f"✗ {str(e)}", severity="error")
