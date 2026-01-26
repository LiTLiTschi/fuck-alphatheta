"""
Shape Preview Window

Lightweight overlay window for previewing shapes during configuration.
Unlike OverlayWindow, this shows a single shape at a time without MIDI processing.
"""

from typing import Dict, Any
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
import sys


class ShapePreviewWindow(QWidget):
    """
    Lightweight overlay window for previewing shapes during configuration.

    Unlike OverlayWindow, this:
    - Shows a single shape at a time
    - Doesn't process MIDI
    - Can be created/destroyed dynamically
    """

    def __init__(self, shape_config: Dict[str, Any]):
        """
        Initialize the preview window.

        Args:
            shape_config: Shape configuration (id, type, position, size, color)
        """
        super().__init__()
        self.shape_config = shape_config
        self._init_window()
        self._create_shape()

    def _init_window(self):
        """Initialize transparent, fullscreen, always-on-top window."""
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, 3840, 2160)  # Fullscreen

    def _create_shape(self):
        """Create shape instance from config."""
        from .shapes.static_shape import StaticShape

        # Create shape with dummy MIDI config (not used for preview)
        config = {
            **self.shape_config,
            'trigger_midi': {'type': 'note', 'channel': 0, 'note': 60}
        }
        self.shape = StaticShape(config)
        self.shape.set_visible(True)  # Always visible for preview

    def paintEvent(self, event):
        """Draw the shape."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.shape and self.shape.visible:
            self.shape.draw(painter)

        painter.end()
