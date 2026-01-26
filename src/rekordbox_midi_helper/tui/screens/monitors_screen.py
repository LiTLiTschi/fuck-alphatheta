"""
Screen Monitors Management Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Button, Static
from textual.containers import Container, Horizontal


class MonitorsScreen(Screen):
    """Screen monitors CRUD screen"""

    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("escape", "app.pop_screen", "Back"),
        ("b", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the monitors layout"""
        yield Header()

        with Container(id="monitors-container"):
            yield Static("Screen Monitors", id="screen-title")
            yield DataTable(id="monitors-table")

            with Horizontal(id="actions"):
                yield Button("Add Monitor", variant="success", id="btn-add")
                yield Button("Edit", variant="primary", id="btn-edit")
                yield Button("Delete", variant="error", id="btn-delete")
                yield Button("Back", variant="default", id="btn-back")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize table with data"""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Add columns
        table.add_columns("ID", "Position", "Target Color", "Tolerance", "MIDI")

        # TODO: Load actual data
        # Placeholder data
        table.add_row("monitor_1", "(100, 100)", "RGB(255,0,0)", "15", "Ch1 CC10")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "btn-add":
            self.action_add()
        elif event.button.id == "btn-edit":
            self.action_edit()
        elif event.button.id == "btn-delete":
            self.action_delete()
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def action_add(self) -> None:
        """Add new monitor"""
        self.notify("Add Monitor - Coming soon!")

    def action_edit(self) -> None:
        """Edit selected monitor"""
        self.notify("Edit Monitor - Coming soon!")

    def action_delete(self) -> None:
        """Delete selected monitor"""
        self.notify("Delete Monitor - Coming soon!")
