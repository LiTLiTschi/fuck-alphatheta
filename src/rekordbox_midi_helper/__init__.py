"""
Rekordbox MIDI Helper

A Python-based solution to enhance Rekordbox DJ software usability with
Bome MIDI Translator Pro, designed to work around hardware limitations.

Copyright (c) 2026 LiTLiTschi
"""

__version__ = "1.2.2"
__author__ = "LiTLiTschi"

# Expose main classes for programmatic usage
from .main import RekordboxMIDIHelper
from .config_loader import ConfigLoader, ConfigValidationError

__all__ = [
    'RekordboxMIDIHelper',
    'ConfigLoader',
    'ConfigValidationError',
]
