"""
Animated Shapes Management Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Button, Static
from textual.containers import Container, Horizontal


class AnimatedShapesScreen(Screen):
    """Animated shapes CRUD screen"""

    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("escape", "app.pop_screen", "Back"),
        ("b", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the shapes layout"""
        yield Header()

        with Container(id="shapes-container"):
            yield Static("Animated Shapes", id="screen-title")
            yield DataTable(id="shapes-table")

            with Horizontal(id="actions"):
                yield Button("Add Shape", variant="success", id="btn-add")
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
        table.add_columns("ID", "Type", "Position", "Size", "MIDI CC", "Animation")

        # TODO: Load actual data
        # Placeholder data
        table.add_row("anim_1", "pie_chart", "(300, 300)", "r=80", "Ch1 CC11", "clockwise")

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
        """Add new animated shape"""
        self.notify("Add Animated Shape - Coming soon!")

    def action_edit(self) -> None:
        """Edit selected shape"""
        self.notify("Edit Shape - Coming soon!")

    def action_delete(self) -> None:
        """Delete selected shape"""
        self.notify("Delete Shape - Coming soon!")
