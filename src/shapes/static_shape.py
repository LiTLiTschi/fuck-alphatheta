"""
Static shapes for overlay - triggered by MIDI Note On/Off.

Static shapes appear when a specific MIDI note is on,
and disappear when the note is off.

Supported shape types:
- circle: Simple circle
- rectangle: Simple rectangle
"""

from typing import Dict, Any
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt

from shapes.base_shape import BaseShape


class StaticShape(BaseShape):
    """
    Static shape that appears/disappears based on MIDI notes.

    The shape is shown when the configured MIDI note is on,
    and hidden when the note is off.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize static shape.

        Args:
            config: Shape configuration from config file
        """
        super().__init__(config)

        # MIDI trigger configuration
        trigger = config['trigger_midi']
        self.trigger_type = trigger['type']  # "note" or "cc"
        self.trigger_channel = trigger['channel']

        if self.trigger_type == 'note':
            self.trigger_note = trigger['note']
        elif self.trigger_type == 'cc':
            self.trigger_controller = trigger.get('controller', 0)
            self.trigger_threshold = trigger.get('threshold', 64)  # CC value to trigger visibility

        # Start hidden
        self.visible = False

    def draw(self, painter: QPainter):
        """
        Draw the shape if visible.

        Args:
            painter: QPainter instance
        """
        if not self.visible:
            return

        # Set up color with alpha
        color = QColor(self.r, self.g, self.b, self.a)
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))

        # Draw based on shape type
        if self.type == 'circle':
            self._draw_circle(painter)
        elif self.type == 'rectangle':
            self._draw_rectangle(painter)

    def _draw_circle(self, painter: QPainter):
        """Draw a circle shape."""
        radius = self.size.get('radius', 30)
        # drawEllipse draws from center
        painter.drawEllipse(
            int(self.x - radius),
            int(self.y - radius),
            int(radius * 2),
            int(radius * 2)
        )

    def _draw_rectangle(self, painter: QPainter):
        """Draw a rectangle shape."""
        width = self.size.get('width', 60)
        height = self.size.get('height', 60)
        # Draw rectangle from top-left corner
        painter.drawRect(
            int(self.x),
            int(self.y),
            int(width),
            int(height)
        )

    def handle_midi(self, midi_event: Dict[str, Any]):
        """
        Handle incoming MIDI event to control visibility.

        Args:
            midi_event: MIDI event dict with type, channel, data1, data2
        """
        # Check if this MIDI event is for this shape
        if midi_event['channel'] != self.trigger_channel:
            return

        if self.trigger_type == 'note':
            # Check if it's our note
            if midi_event['type'] in ['note_on', 'note_off']:
                note = midi_event['data1']
                velocity = midi_event['data2']

                if note == self.trigger_note:
                    # Note on with velocity > 0 = show
                    # Note off or note on with velocity 0 = hide
                    if midi_event['type'] == 'note_on' and velocity > 0:
                        self.set_visible(True)
                    else:
                        self.set_visible(False)

        elif self.trigger_type == 'cc':
            # CC trigger - show if value above threshold
            if midi_event['type'] == 'cc':
                controller = midi_event['data1']
                value = midi_event['data2']

                if controller == self.trigger_controller:
                    self.set_visible(value >= self.trigger_threshold)
