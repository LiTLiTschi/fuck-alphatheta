"""
Static Shapes Management Screen
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Button, Static
from textual.containers import Container, Horizontal


class StaticShapesScreen(Screen):
    """Static shapes CRUD screen"""

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
            yield Static("Static Shapes", id="screen-title")
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
        table.add_columns("ID", "Type", "Position", "Size", "MIDI", "Behavior")

        # Load actual data
        self.refresh_table()

    def refresh_table(self) -> None:
        """Refresh table with current data"""
        table = self.query_one(DataTable)
        table.clear()

        shapes = self.app.config_service.get_static_shapes()

        if not shapes:
            table.add_row("", "[dim]No static shapes configured[/]", "", "", "", "")
        else:
            for shape in shapes:
                shape_id = shape.get('id', 'Unknown')
                shape_type = shape.get('type', 'unknown')

                # Position
                pos = shape.get('position', {})
                position = f"({pos.get('x', 0)}, {pos.get('y', 0)})"

                # Size
                size_data = shape.get('size', {})
                if 'radius' in size_data:
                    size = f"r={size_data['radius']}"
                elif 'width' in size_data and 'height' in size_data:
                    size = f"{size_data['width']}x{size_data['height']}"
                else:
                    size = "?"

                # MIDI trigger
                midi = shape.get('trigger_midi', {})
                if isinstance(midi, dict):
                    midi_str = f"Ch{midi.get('channel', 0)+1} Note{midi.get('note', 0)}"
                else:
                    midi_str = str(midi)

                # Behavior
                behavior = shape.get('behavior', {})
                if isinstance(behavior, dict):
                    note_on = behavior.get('note_on', 'none')
                    note_off = behavior.get('note_off', 'none')
                    behavior_str = f"{note_on}/{note_off}"
                else:
                    behavior_str = str(behavior)

                table.add_row(shape_id, shape_type, position, size, midi_str, behavior_str, key=shape_id)

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
        """Add new shape"""
        self.notify("Add Static Shape - Coming in Phase 5!")

    def action_edit(self) -> None:
        """Edit selected shape"""
        self.notify("Edit Shape - Coming in Phase 5!")

    def action_delete(self) -> None:
        """Delete selected shape"""
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)[0]
            if row_key and row_key != "":
                self.app.config_service.delete_static_shape(row_key)
                self.refresh_table()
                self.notify(f"✓ Deleted shape '{row_key}'")
