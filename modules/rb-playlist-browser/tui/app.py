from pathlib import Path

from textual.app import App
from textual.binding import Binding

from .screens.browser import BrowserScreen


class PlaylistBrowserApp(App):
    TITLE = "RB Playlist Browser"
    SUB_TITLE = "Rekordbox XML Playlist Manager"
    CSS_PATH = "styles/main.tcss"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(self, xml_path: Path):
        super().__init__()
        self.xml_path = xml_path

    def on_mount(self) -> None:
        self.push_screen(BrowserScreen(self.xml_path))
