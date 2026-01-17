"""
MIDI message utility functions for creating and parsing MIDI messages.
"""

from typing import List, Tuple


def create_note_on(channel: int, note: int, velocity: int) -> List[int]:
    """
    Create a MIDI Note On message.

    Args:
        channel: MIDI channel (1-16)
        note: Note number (0-127)
        velocity: Note velocity (0-127)

    Returns:
        MIDI message as list of integers [status, note, velocity]
    """
    status = 0x90 | (channel - 1)  # Note On is 0x90, channels are 0-indexed
    return [status, note & 0x7F, velocity & 0x7F]


def create_note_off(channel: int, note: int, velocity: int = 0) -> List[int]:
    """
    Create a MIDI Note Off message.

    Args:
        channel: MIDI channel (1-16)
        note: Note number (0-127)
        velocity: Note velocity (0-127), typically 0

    Returns:
        MIDI message as list of integers [status, note, velocity]
    """
    status = 0x80 | (channel - 1)  # Note Off is 0x80
    return [status, note & 0x7F, velocity & 0x7F]


def create_cc(channel: int, controller: int, value: int) -> List[int]:
    """
    Create a MIDI Control Change (CC) message.

    Args:
        channel: MIDI channel (1-16)
        controller: Controller number (0-127)
        value: Controller value (0-127)

    Returns:
        MIDI message as list of integers [status, controller, value]
    """
    status = 0xB0 | (channel - 1)  # CC is 0xB0
    return [status, controller & 0x7F, value & 0x7F]


def parse_midi_message(message: List[int]) -> Tuple[str, int, int, int]:
    """
    Parse a MIDI message into its components.

    Args:
        message: MIDI message as list of integers

    Returns:
        Tuple of (message_type, channel, data1, data2)
        message_type is one of: "note_on", "note_off", "cc", "unknown"
    """
    if len(message) < 3:
        return ("unknown", 0, 0, 0)

    status = message[0]
    channel = (status & 0x0F) + 1  # Convert 0-indexed to 1-indexed
    data1 = message[1]
    data2 = message[2]

    msg_type = status & 0xF0
    if msg_type == 0x90:
        # Note On with velocity 0 is sometimes used as Note Off
        if data2 == 0:
            return ("note_off", channel, data1, data2)
        return ("note_on", channel, data1, data2)
    elif msg_type == 0x80:
        return ("note_off", channel, data1, data2)
    elif msg_type == 0xB0:
        return ("cc", channel, data1, data2)
    else:
        return ("unknown", channel, data1, data2)


def scale_value(value: int, from_range: Tuple[int, int], to_range: Tuple[int, int]) -> int:
    """
    Scale a value from one range to another.

    Useful for mapping MIDI CC values (0-127) to other ranges like angles (0-360).

    Args:
        value: Value to scale
        from_range: Source range as (min, max)
        to_range: Destination range as (min, max)

    Returns:
        Scaled value as integer
    """
    from_min, from_max = from_range
    to_min, to_max = to_range

    # Clamp value to from_range
    value = max(from_min, min(value, from_max))

    # Scale to 0-1
    normalized = (value - from_min) / (from_max - from_min)

    # Scale to target range
    scaled = to_min + (normalized * (to_max - to_min))

    return int(scaled)


def clamp_midi_value(value: int) -> int:
    """
    Clamp a value to valid MIDI range (0-127).

    Args:
        value: Value to clamp

    Returns:
        Clamped value between 0 and 127
    """
    return max(0, min(value, 127))
