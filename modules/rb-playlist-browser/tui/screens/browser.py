from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Tree, DataTable, Static, Input
from textual.widget import Widget
from textual.containers import Horizontal, Vertical
from textual import on

from xml_reader import Library, PlaylistNode, load
from xml_writer import rename_node, delete_node, save


class RenameBar(Widget):
    """Inline rename widget docked at bottom."""

    def compose(self) -> ComposeResult:
        yield Static("Rename:", id="rename-label")
        yield Input(placeholder="New name…", id="rename-input")


class BrowserScreen(Screen):
    BINDINGS = [
        Binding("r", "rename", "Rename", show=True),
        Binding("d", "delete", "Delete", show=True),
        Binding("s", "save", "Save", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("q", "quit_app", "Quit", show=True),
    ]

    def __init__(self, xml_path: Path):
        super().__init__()
        self.xml_path = xml_path
        self.library: Library = load(xml_path)
        self._selected_node: PlaylistNode | None = None
        self._selected_parent: PlaylistNode | None = None
        self._node_map: dict[int, tuple[PlaylistNode, PlaylistNode | None]] = {}
        self._unsaved = False
        self._renaming = False
        self._quit_warned = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="browser-container"):
            with Vertical(id="tree-pane"):
                yield Tree("📚 Library", id="playlist-tree")
            with Vertical(id="detail-pane"):
                yield Static("← Select a playlist", id="detail-title")
                yield DataTable(id="track-table")
        yield Footer()

    def on_mount(self) -> None:
        self._build_tree()
        table = self.query_one("#track-table", DataTable)
        table.add_columns("Artist", "Title", "Path")
        table.cursor_type = "row"

    def _build_tree(self) -> None:
        tree = self.query_one("#playlist-tree", Tree)
        tree.clear()
        self._node_map.clear()
        self._populate_tree_node(tree.root, self.library.root, parent_model=None)
        tree.root.expand()

    def _populate_tree_node(self, tree_node, model: PlaylistNode, parent_model):
        for child in model.children:
            label = f"📁 {child.name}" if child.is_folder else f"🎵 {child.name} ({len(child.track_ids)})"
            branch = tree_node.add(label, expand=False)
            self._node_map[id(branch)] = (child, model)
            self._populate_tree_node(branch, child, model)

    @on(Tree.NodeSelected, "#playlist-tree")
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        key = id(event.node)
        if key not in self._node_map:
            return
        model, parent = self._node_map[key]
        self._selected_node = model
        self._selected_parent = parent
        self._quit_warned = False

        title = self.query_one("#detail-title", Static)
        table = self.query_one("#track-table", DataTable)
        table.clear()

        if model.is_folder:
            title.update(f"📁 [bold]{model.name}[/bold]  —  {len(model.children)} item(s)")
        else:
            title.update(f"🎵 [bold]{model.name}[/bold]  —  {len(model.track_ids)} track(s)")
            for tid in model.track_ids:
                track = self.library.tracks.get(tid)
                if track:
                    table.add_row(track.artist, track.name, track.path)
                else:
                    table.add_row("?", f"Unknown (ID {tid})", "")

    def action_rename(self) -> None:
        if not self._selected_node:
            self.notify("Select a playlist or folder first", severity="warning")
            return
        if self._renaming:
            return
        self._renaming = True
        bar = RenameBar()
        self.mount(bar)
        inp = bar.query_one("#rename-input", Input)
        inp.value = self._selected_node.name
        inp.focus()

    @on(Input.Submitted, "#rename-input")
    def on_rename_submitted(self, event: Input.Submitted) -> None:
        new_name = event.value.strip()
        if new_name and self._selected_node:
            rename_node(self.library, self._selected_node, new_name)
            self._unsaved = True
            self.notify(f"Renamed to '{new_name}'")
            self._build_tree()
        self._cancel_rename()

    def _cancel_rename(self) -> None:
        self._renaming = False
        for bar in self.query(RenameBar):
            bar.remove()
        self.query_one("#playlist-tree", Tree).focus()

    def action_cancel(self) -> None:
        if self._renaming:
            self._cancel_rename()

    def action_delete(self) -> None:
        if not self._selected_node or not self._selected_parent:
            self.notify("Select a playlist or folder first", severity="warning")
            return
        name = self._selected_node.name
        delete_node(self.library, self._selected_node, self._selected_parent)
        self._selected_node = None
        self._selected_parent = None
        self._unsaved = True
        self.notify(f"Deleted '{name}'", severity="warning")
        self._build_tree()
        self.query_one("#detail-title", Static).update("← Select a playlist")
        self.query_one("#track-table", DataTable).clear()

    def action_save(self) -> None:
        try:
            save(self.library, self.xml_path)
            self._unsaved = False
            self._quit_warned = False
            self.notify("✓ Saved", severity="information")
        except Exception as e:
            self.notify(f"✗ Save failed: {e}", severity="error")

    def action_quit_app(self) -> None:
        if self._unsaved and not self._quit_warned:
            self._quit_warned = True
            self.notify("Unsaved changes! Press S to save, or Q again to force quit.", severity="warning")
            return
        self.app.exit()
