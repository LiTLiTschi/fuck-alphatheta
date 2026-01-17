"""
Animated shapes for overlay - controlled by MIDI CC values.

Animated shapes change their appearance based on incoming MIDI CC values.
The most common use case is a pie chart that fills from 0-360 degrees
based on a CC value from 0-127.

Supported shape types:
- pie_chart: Circle that fills like a pie chart based on CC value
- progress_bar: Horizontal or vertical bar that fills based on CC value
"""

from typing import Dict, Any
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import Qt

from shapes.base_shape import BaseShape
from utils.midi_utils import scale_value


class AnimatedShape(BaseShape):
    """
    Animated shape controlled by MIDI CC values.

    The shape's appearance changes dynamically based on the CC value (0-127).
    For example, a pie chart fills from 0° to 360° as CC goes from 0 to 127.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize animated shape.

        Args:
            config: Shape configuration from config file
        """
        super().__init__(config)

        # MIDI control configuration
        control = config['control_midi']
        self.control_type = control['type']  # Should be "cc"
        self.control_channel = control['channel']
        self.control_controller = control.get('controller', 0)

        # Animation parameters
        animation = config.get('animation', {})
        self.start_angle = animation.get('start_angle', 0)
        self.end_angle_range = animation.get('end_angle_range', [0, 360])
        self.fill_direction = animation.get('fill_direction', 'clockwise')
        self.direction = animation.get('direction', 'horizontal')  # For progress bars

        # Current CC value (0-127)
        self.current_cc_value = 0

        # Current angle or fill percentage (calculated from CC value)
        self.current_angle = 0  # For pie charts
        self.current_fill_percent = 0.0  # For progress bars

        # Animated shapes are always visible (but may show as empty at CC=0)
        self.visible = True

    def draw(self, painter: QPainter):
        """
        Draw the animated shape.

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
        if self.type == 'pie_chart':
            self._draw_pie_chart(painter)
        elif self.type == 'progress_bar':
            self._draw_progress_bar(painter)

    def _draw_pie_chart(self, painter: QPainter):
        """
        Draw a pie chart that fills based on current angle.

        Qt's drawPie uses 1/16th degree units and angles start at 3 o'clock
        going counter-clockwise. We adjust for more intuitive top-starting clockwise.
        """
        radius = self.size.get('radius', 50)
        diameter = radius * 2

        # Qt angles: 0° is at 3 o'clock, positive goes counter-clockwise
        # We want 0° at top (12 o'clock), so start at 90° and go clockwise
        # Convert our angle to Qt's angle system
        qt_start_angle = 90 * 16  # Start at top (12 o'clock position)

        # Calculate span angle based on current CC value
        span_angle = self.current_angle

        # If fill direction is counter-clockwise, negate the span
        if self.fill_direction == 'counterclockwise':
            span_angle = -span_angle

        # Draw the pie
        # drawPie arguments: (x, y, width, height, start_angle*16, span_angle*16)
        painter.drawPie(
            int(self.x - radius),
            int(self.y - radius),
            int(diameter),
            int(diameter),
            qt_start_angle,
            int(span_angle * 16)
        )

        # Optional: Draw outline circle for better visibility when empty
        if self.current_angle < 5:  # Nearly empty
            outline_color = QColor(self.r, self.g, self.b, min(100, self.a))
            painter.setPen(QPen(outline_color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(
                int(self.x - radius),
                int(self.y - radius),
                int(diameter),
                int(diameter)
            )

    def _draw_progress_bar(self, painter: QPainter):
        """Draw a progress bar that fills based on current fill percentage."""
        width = self.size.get('width', 200)
        height = self.size.get('height', 20)

        # Draw background/outline
        outline_color = QColor(self.r, self.g, self.b, min(100, self.a))
        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(int(self.x), int(self.y), int(width), int(height))

        # Draw filled portion
        if self.current_fill_percent > 0:
            fill_color = QColor(self.r, self.g, self.b, self.a)
            painter.setBrush(QBrush(fill_color))
            painter.setPen(Qt.NoPen)

            if self.direction == 'horizontal':
                # Fill from left to right
                if self.fill_direction in ['left_to_right', 'clockwise']:
                    fill_width = int(width * self.current_fill_percent)
                    painter.drawRect(int(self.x), int(self.y), fill_width, int(height))
                else:  # right_to_left
                    fill_width = int(width * self.current_fill_percent)
                    fill_x = int(self.x + width - fill_width)
                    painter.drawRect(fill_x, int(self.y), fill_width, int(height))

            else:  # vertical
                if self.fill_direction in ['bottom_to_top', 'counterclockwise']:
                    fill_height = int(height * self.current_fill_percent)
                    fill_y = int(self.y + height - fill_height)
                    painter.drawRect(int(self.x), fill_y, int(width), fill_height)
                else:  # top_to_bottom
                    fill_height = int(height * self.current_fill_percent)
                    painter.drawRect(int(self.x), int(self.y), int(width), fill_height)

    def handle_midi(self, midi_event: Dict[str, Any]):
        """
        Handle incoming MIDI CC event to update animation.

        Args:
            midi_event: MIDI event dict with type, channel, data1, data2
        """
        # Check if this MIDI event is for this shape
        if midi_event['type'] != 'cc':
            return

        if midi_event['channel'] != self.control_channel:
            return

        controller = midi_event['data1']
        if controller != self.control_controller:
            return

        # Update current CC value
        self.current_cc_value = midi_event['data2']

        # Update angle or fill percentage based on shape type
        if self.type == 'pie_chart':
            # Scale CC value (0-127) to angle range
            self.current_angle = scale_value(
                self.current_cc_value,
                (0, 127),
                tuple(self.end_angle_range)
            )

        elif self.type == 'progress_bar':
            # Scale CC value (0-127) to percentage (0.0-1.0)
            self.current_fill_percent = self.current_cc_value / 127.0

    def get_current_value(self) -> int:
        """
        Get current CC value.

        Returns:
            Current CC value (0-127)
        """
        return self.current_cc_value
