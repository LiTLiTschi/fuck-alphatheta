"""
Color utility functions for RGB comparison and detection.
"""

import numpy as np
from typing import Tuple


def color_matches(pixel_rgb: Tuple[int, int, int],
                  target_rgb: Tuple[int, int, int],
                  tolerance: int) -> bool:
    """
    Check if a pixel color matches a target color within tolerance.

    Uses simple RGB distance comparison for performance.

    Args:
        pixel_rgb: RGB tuple (r, g, b) of the pixel to check
        target_rgb: RGB tuple (r, g, b) of the target color
        tolerance: Maximum allowed difference per channel (0-255)

    Returns:
        True if the color matches within tolerance, False otherwise
    """
    return (
        abs(pixel_rgb[0] - target_rgb[0]) <= tolerance and
        abs(pixel_rgb[1] - target_rgb[1]) <= tolerance and
        abs(pixel_rgb[2] - target_rgb[2]) <= tolerance
    )


def euclidean_color_distance(pixel_rgb: Tuple[int, int, int],
                             target_rgb: Tuple[int, int, int]) -> float:
    """
    Calculate Euclidean distance between two colors in RGB space.

    Args:
        pixel_rgb: RGB tuple (r, g, b) of the pixel
        target_rgb: RGB tuple (r, g, b) of the target color

    Returns:
        Euclidean distance as a float
    """
    return np.sqrt(
        (pixel_rgb[0] - target_rgb[0]) ** 2 +
        (pixel_rgb[1] - target_rgb[1]) ** 2 +
        (pixel_rgb[2] - target_rgb[2]) ** 2
    )


def average_region_color(pixel_data: np.ndarray) -> Tuple[int, int, int]:
    """
    Calculate the average color of a region.

    Useful for reducing noise when monitoring screen regions.

    Args:
        pixel_data: Numpy array of shape (height, width, 3) or (height, width, 4)

    Returns:
        Average RGB color as (r, g, b) tuple
    """
    # Handle both RGB and RGBA
    if pixel_data.shape[2] == 4:
        pixel_data = pixel_data[:, :, :3]

    avg_color = np.mean(pixel_data, axis=(0, 1))
    return tuple(avg_color.astype(int))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """
    Convert RGB tuple to hex string.

    Args:
        rgb: RGB tuple (r, g, b)

    Returns:
        Hex color string like "#FF0000"
    """
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.

    Args:
        hex_color: Hex color string like "#FF0000" or "FF0000"

    Returns:
        RGB tuple (r, g, b)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
