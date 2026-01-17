"""
MIDI handler for creating virtual ports and sending/receiving MIDI messages.

This module manages:
- Virtual MIDI port creation using python-rtmidi
- MIDI output thread (sends messages from screen monitor)
- MIDI input thread (receives CC messages for shape control)

Threading: Uses two separate threads for input and output
Integration: Works with Bome MIDI Translator Pro
"""

import rtmidi
from threading import Thread
from typing import Dict, Any, Optional, List
import time

from .utils.midi_utils import create_note_on, create_note_off, create_cc, parse_midi_message
from .utils.threading_utils import ThreadSafeQueue, ShutdownEvent


class MIDIHandler:
    """
    Manages virtual MIDI ports and message routing.

    Creates a virtual MIDI input and output port, then spawns threads to:
    - Send MIDI messages from the screen monitor queue
    - Receive MIDI messages and forward to the overlay window queue

    Example:
        handler = MIDIHandler(
            port_name="Rekordbox Helper",
            output_queue=midi_to_overlay_queue,
            shutdown_event=shutdown_event
        )
        handler.start()
        # ... application runs ...
        handler.stop()
    """

    def __init__(self,
                 port_name: str,
                 midi_to_overlay_queue: ThreadSafeQueue,
                 shutdown_event: ShutdownEvent,
                 debug: bool = False):
        """
        Initialize MIDI handler.

        Args:
            port_name: Name for the virtual MIDI ports
            midi_to_overlay_queue: Queue to send received MIDI to overlay
            shutdown_event: Event to signal thread shutdown
            debug: Enable debug logging
        """
        self.port_name = port_name
        self.midi_to_overlay_queue = midi_to_overlay_queue
        self.shutdown_event = shutdown_event
        self.debug = debug

        # MIDI port instances
        self.midi_out: Optional[rtmidi.MidiOut] = None
        self.midi_in: Optional[rtmidi.MidiIn] = None

        # Threads
        self.output_thread: Optional[Thread] = None
        self.input_thread: Optional[Thread] = None

        # Queue for messages to send out
        self.send_queue = ThreadSafeQueue()

    def start(self):
        """
        Create virtual MIDI ports and start send/receive threads.

        Raises:
            RuntimeError: If MIDI ports cannot be created
        """
        try:
            # Create MIDI output port (we send to Bome through this)
            self.midi_out = rtmidi.MidiOut()
            self.midi_out.open_virtual_port(f"{self.port_name} Out")

            # Create MIDI input port (we receive from Bome through this)
            self.midi_in = rtmidi.MidiIn()
            self.midi_in.open_virtual_port(f"{self.port_name} In")

            # Set callback for incoming MIDI messages
            self.midi_in.set_callback(self._midi_callback)

            if self.debug:
                print(f"[MIDI] Created virtual ports: '{self.port_name} Out' and '{self.port_name} In'")

            # Start output thread (sends MIDI from queue)
            self.output_thread = Thread(
                target=self._output_worker,
                daemon=True,
                name="MIDIOutput"
            )
            self.output_thread.start()

            if self.debug:
                print("[MIDI] Started MIDI threads")

        except Exception as e:
            raise RuntimeError(f"Failed to create MIDI ports: {e}")

    def stop(self):
        """
        Stop MIDI threads and close ports.
        """
        if self.debug:
            print("[MIDI] Stopping MIDI handler...")

        # Wait for threads to finish
        if self.output_thread and self.output_thread.is_alive():
            self.output_thread.join(timeout=2.0)

        # Close MIDI ports
        if self.midi_out:
            try:
                self.midi_out.close_port()
            except:
                pass

        if self.midi_in:
            try:
                self.midi_in.close_port()
            except:
                pass

        if self.debug:
            print("[MIDI] MIDI handler stopped")

    def send_from_screen_monitor(self, event: Dict[str, Any]):
        """
        Send MIDI message based on screen monitor event.

        Args:
            event: Screen monitor event with midi_config and match state
        """
        midi_config = event['midi_config']
        is_matched = event['matched']

        # Build MIDI message based on type
        if midi_config['type'] == 'note':
            # Note On/Off message
            channel = midi_config['channel']
            note = midi_config['note']

            if is_matched:
                velocity = midi_config.get('velocity_on', 127)
                message = create_note_on(channel, note, velocity)
            else:
                velocity = midi_config.get('velocity_off', 0)
                message = create_note_off(channel, note, velocity)

        elif midi_config['type'] == 'cc':
            # Control Change message
            channel = midi_config['channel']
            controller = midi_config['controller']

            if is_matched:
                value = midi_config.get('value_match', 127)
            else:
                value = midi_config.get('value_nomatch', 0)

            message = create_cc(channel, controller, value)

        else:
            if self.debug:
                print(f"[MIDI] Unknown MIDI type: {midi_config['type']}")
            return

        # Queue message for sending
        self.send_queue.put(message)

    def _output_worker(self):
        """
        Worker thread that sends MIDI messages from queue.

        Runs until shutdown_event is set.
        """
        if self.debug:
            print("[MIDI] Output worker started")

        while not self.shutdown_event.is_set():
            # Check for messages to send (non-blocking with timeout)
            try:
                message = self.send_queue.get(block=True, timeout=0.1)
                if message:
                    self._send_message(message)
            except:
                # Timeout or empty queue - continue
                pass

        if self.debug:
            print("[MIDI] Output worker stopped")

    def _send_message(self, message: List[int]):
        """
        Send a MIDI message through the output port.

        Args:
            message: MIDI message as list of integers
        """
        if self.midi_out is None:
            return

        try:
            self.midi_out.send_message(message)

            if self.debug:
                msg_type, channel, data1, data2 = parse_midi_message(message)
                print(f"[MIDI] Sent: {msg_type} CH{channel} D1:{data1} D2:{data2}")

        except Exception as e:
            if self.debug:
                print(f"[MIDI] Error sending message: {e}")

    def _midi_callback(self, event, data=None):
        """
        Callback for incoming MIDI messages.

        This is called by python-rtmidi when a message is received.

        Args:
            event: Tuple of (message, delta_time)
            data: Optional user data (unused)
        """
        message, delta_time = event

        # Parse message
        msg_type, channel, data1, data2 = parse_midi_message(message)

        if self.debug:
            print(f"[MIDI] Received: {msg_type} CH{channel} D1:{data1} D2:{data2}")

        # Forward to overlay window queue
        # We're mainly interested in CC messages for shape control
        if msg_type in ['cc', 'note_on', 'note_off']:
            midi_event = {
                'type': msg_type,
                'channel': channel,
                'data1': data1,  # Note number or CC controller
                'data2': data2   # Velocity or CC value
            }
            self.midi_to_overlay_queue.put(midi_event)

    def is_running(self) -> bool:
        """
        Check if MIDI handler is running.

        Returns:
            True if both ports are open and threads are running
        """
        return (
            self.midi_out is not None and
            self.midi_in is not None and
            self.output_thread is not None and
            self.output_thread.is_alive()
        )
