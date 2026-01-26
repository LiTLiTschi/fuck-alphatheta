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

        # TODO: Load actual data
        # Placeholder data
        table.add_row("default", "3", "5", "2", "[green]Active[/]")
        table.add_row("backup", "3", "4", "1", "")

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
        self.notify("Switch Preset - Coming soon!")

    def action_new(self) -> None:
        """Create new preset"""
        self.notify("New Preset - Coming soon!")

    def action_copy(self) -> None:
        """Copy preset"""
        self.notify("Copy Preset - Coming soon!")

    def action_delete(self) -> None:
        """Delete preset"""
        self.notify("Delete Preset - Coming soon!")
