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

        # Load actual data
        self.refresh_table()

    def refresh_table(self) -> None:
        """Refresh table with current data"""
        table = self.query_one(DataTable)
        table.clear()

        monitors = self.app.config_service.get_screen_monitors()

        if not monitors:
            # No data row
            table.add_row("", "[dim]No monitors configured[/]", "", "", "")
        else:
            for monitor in monitors:
                monitor_id = monitor.get('id', 'Unknown')

                # Position - support both formats
                if 'position' in monitor:
                    pos = monitor['position']
                    position = f"({pos['x']}, {pos['y']})"
                elif 'region' in monitor:
                    reg = monitor['region']
                    position = f"({reg['x']}, {reg['y']})"
                else:
                    position = "?"

                # Target color
                color = monitor.get('target_color', {})
                if isinstance(color, dict):
                    target_color = f"RGB({color.get('r', 0)},{color.get('g', 0)},{color.get('b', 0)})"
                else:
                    target_color = str(color)

                # Tolerance
                tolerance = str(monitor.get('tolerance', 0))

                # MIDI output
                midi = monitor.get('midi_output', {})
                if isinstance(midi, dict):
                    midi_str = f"Ch{midi.get('channel', 0)+1} CC{midi.get('controller', 0)}"
                else:
                    midi_str = str(midi)

                table.add_row(monitor_id, position, target_color, tolerance, midi_str, key=monitor_id)

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
