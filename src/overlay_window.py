"""
Transparent overlay window for drawing shapes on top of Rekordbox.

This module creates a Qt window that is:
- Transparent (click-through)
- Always on top
- Frameless (no window decorations)

The window draws static and animated shapes based on MIDI input.

Threading: Runs in the main thread (Qt event loop)
Performance: Repaints only when MIDI events change shape state
"""

from typing import List, Dict, Any
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import Qt, QTimer

from shapes.static_shape import StaticShape
from shapes.animated_shape import AnimatedShape
from utils.threading_utils import ThreadSafeQueue


class OverlayWindow(QWidget):
    """
    Transparent, always-on-top overlay window for drawing shapes.

    This window sits on top of all other windows but allows clicks to
    pass through to the underlying applications (like Rekordbox).

    Shapes are updated based on MIDI events from the MIDI input queue.
    """

    def __init__(self,
                 shapes_config: Dict[str, List[Dict[str, Any]]],
                 midi_input_queue: ThreadSafeQueue,
                 debug: bool = False):
        """
        Initialize overlay window.

        Args:
            shapes_config: Dictionary with 'static' and 'animated' shape configs
            midi_input_queue: Queue to receive MIDI events from
            debug: Enable debug mode
        """
        super().__init__()

        self.midi_input_queue = midi_input_queue
        self.debug = debug

        # Create shape instances
        self.static_shapes: List[StaticShape] = []
        self.animated_shapes: List[AnimatedShape] = []

        self._create_shapes(shapes_config)
        self._setup_window()

        # Timer to check MIDI queue periodically
        self.midi_timer = QTimer(self)
        self.midi_timer.timeout.connect(self._process_midi_queue)
        self.midi_timer.start(10)  # Check every 10ms for low latency

        if self.debug:
            print(f"[Overlay] Created {len(self.static_shapes)} static shapes")
            print(f"[Overlay] Created {len(self.animated_shapes)} animated shapes")

    def _create_shapes(self, shapes_config: Dict[str, List[Dict[str, Any]]]):
        """
        Create shape instances from configuration.

        Args:
            shapes_config: Dictionary with 'static' and 'animated' lists
        """
        # Create static shapes
        for shape_config in shapes_config.get('static', []):
            try:
                shape = StaticShape(shape_config)
                self.static_shapes.append(shape)
            except Exception as e:
                if self.debug:
                    print(f"[Overlay] Error creating static shape: {e}")

        # Create animated shapes
        for shape_config in shapes_config.get('animated', []):
            try:
                shape = AnimatedShape(shape_config)
                self.animated_shapes.append(shape)
            except Exception as e:
                if self.debug:
                    print(f"[Overlay] Error creating animated shape: {e}")

    def _setup_window(self):
        """
        Configure window properties for transparent overlay.
        """
        # Set window flags for transparent, always-on-top, click-through window
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # Always on top
            Qt.FramelessWindowHint |   # No window frame
            Qt.Tool |                  # Don't show in taskbar
            Qt.WindowTransparentForInput  # Click-through (Qt 5.15+)
        )

        # For older Qt versions, use this instead:
        # self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Make window transparent
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set window to fullscreen (covers entire screen)
        # Note: You may want to use the screen resolution from config
        # For now, we'll use a large size that covers most screens
        self.setGeometry(0, 0, 3840, 2160)  # Covers up to 4K displays

        # Show the window
        self.show()

        if self.debug:
            print("[Overlay] Window initialized and shown")

    def paintEvent(self, event):
        """
        Paint event handler - draws all shapes.

        This is called automatically by Qt when the window needs repainting.

        Args:
            event: QPaintEvent instance
        """
        painter = QPainter(self)

        # Enable antialiasing for smooth shapes
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw all static shapes
        for shape in self.static_shapes:
            if shape.is_visible():
                shape.draw(painter)

        # Draw all animated shapes
        for shape in self.animated_shapes:
            if shape.is_visible():
                shape.draw(painter)

        painter.end()

    def _process_midi_queue(self):
        """
        Process MIDI events from the queue and update shapes.

        Called periodically by the timer.
        """
        # Process all pending MIDI events
        events = self.midi_input_queue.get_all()

        if not events:
            return

        # Flag to track if we need to repaint
        needs_repaint = False

        for event in events:
            if self.debug:
                print(f"[Overlay] Processing MIDI: {event}")

            # Update static shapes
            for shape in self.static_shapes:
                prev_visible = shape.is_visible()
                shape.handle_midi(event)
                if shape.is_visible() != prev_visible:
                    needs_repaint = True

            # Update animated shapes
            for shape in self.animated_shapes:
                prev_value = shape.get_current_value() if hasattr(shape, 'get_current_value') else None
                shape.handle_midi(event)
                if hasattr(shape, 'get_current_value'):
                    if shape.get_current_value() != prev_value:
                        needs_repaint = True

        # Trigger repaint if any shape changed
        if needs_repaint:
            self.update()

    def closeEvent(self, event):
        """
        Handle window close event.

        Args:
            event: QCloseEvent instance
        """
        if self.debug:
            print("[Overlay] Window closing")

        # Stop the timer
        self.midi_timer.stop()

        event.accept()

    def get_shape_count(self) -> tuple:
        """
        Get count of shapes.

        Returns:
            Tuple of (static_count, animated_count)
        """
        return (len(self.static_shapes), len(self.animated_shapes))
