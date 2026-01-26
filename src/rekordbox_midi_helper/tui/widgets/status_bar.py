"""
Status Bar Widget
"""

from textual.widgets import Static
from rich.text import Text


class StatusBar(Static):
    """Status bar showing preset, unsaved changes, etc."""

    def __init__(self):
        super().__init__()
        self.preset_name = "default"
        self.unsaved = False
        self.update_display()

    def set_preset(self, name: str) -> None:
        """Set active preset name"""
        self.preset_name = name
        self.update_display()

    def set_unsaved(self, unsaved: bool) -> None:
        """Set unsaved changes flag"""
        self.unsaved = unsaved
        self.update_display()

    def update_display(self) -> None:
        """Update the status bar display"""
        text = Text()

        # Preset name
        text.append("Preset: ", style="dim")
        text.append(self.preset_name, style="cyan bold")

        # Unsaved changes indicator
        if self.unsaved:
            text.append("  ", style="")
            text.append("●", style="yellow bold")
            text.append(" Unsaved changes", style="yellow")

        self.update(text)
