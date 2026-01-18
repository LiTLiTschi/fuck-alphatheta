"""Platform detection utilities for MIDI support."""

import sys


def is_windows() -> bool:
    """
    Check if running on Windows.

    Returns:
        True if running on Windows, False otherwise
    """
    return sys.platform == 'win32'
