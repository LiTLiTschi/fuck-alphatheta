"""
Base shape class for overlay shapes.

All shapes inherit from this abstract base class and implement
the draw() method for rendering with QPainter.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from PyQt5.QtGui import QPainter


class BaseShape(ABC):
    """
    Abstract base class for overlay shapes.

    Subclasses must implement the draw() method to render the shape.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize base shape.

        Args:
            config: Shape configuration dictionary from config file
        """
        self.config = config
        self.id = config['id']
        self.type = config['type']

        # Position (all shapes have x, y position)
        self.x = config['position']['x']
        self.y = config['position']['y']

        # Color (RGBA)
        color = config['color']
        self.r = color['r']
        self.g = color['g']
        self.b = color['b']
        self.a = color.get('a', 255)  # Default to fully opaque

        # Size parameters (varies by shape type)
        self.size = config['size']

        # Visibility flag (can be toggled on/off)
        self.visible = False

    @abstractmethod
    def draw(self, painter: QPainter):
        """
        Draw the shape using QPainter.

        This must be implemented by subclasses.

        Args:
            painter: QPainter instance for drawing
        """
        pass

    def set_visible(self, visible: bool):
        """
        Set shape visibility.

        Args:
            visible: True to show, False to hide
        """
        self.visible = visible

    def is_visible(self) -> bool:
        """
        Check if shape is visible.

        Returns:
            True if visible, False otherwise
        """
        return self.visible

    def get_id(self) -> str:
        """Get shape ID."""
        return self.id

    def get_type(self) -> str:
        """Get shape type."""
        return self.type
