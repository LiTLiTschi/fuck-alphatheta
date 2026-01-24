"""
MIDI handler for connecting to loopMIDI and sending/receiving MIDI messages.

This module manages:
- Connection to loopMIDI port (Windows virtual MIDI driver)
- MIDI output thread (sends messages from screen monitor)
- MIDI input thread (receives CC messages for shape control)

Threading: Uses two separate threads for input and output
Integration: Works with Bome MIDI Translator Pro via loopMIDI
"""

import mido
from threading import Thread
from typing import Dict, Any, Optional, List
import time

from .utils.midi_utils import create_note_on, create_note_off, create_cc, parse_midi_message
from .utils.threading_utils import ThreadSafeQueue, ShutdownEvent


class MIDIHandler:
    """
    Manages loopMIDI port connection and message routing.

    Connects to an existing loopMIDI port, then spawns threads to:
    - Send MIDI messages from the screen monitor queue
    - Receive MIDI messages and forward to the overlay window queue

    Example:
        handler = MIDIHandler(
            port_name="loopMIDI Port",
            midi_to_overlay_queue=midi_to_overlay_queue,
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
            port_name: Name of the loopMIDI port to connect to
            midi_to_overlay_queue: Queue to send received MIDI to overlay
            shutdown_event: Event to signal thread shutdown
            debug: Enable debug logging
        """
        self.port_name = port_name
        self.midi_to_overlay_queue = midi_to_overlay_queue
        self.shutdown_event = shutdown_event
        self.debug = debug

        # Separate MIDI input and output ports (loopMIDI creates these separately)
        self.midi_out: Optional[mido.ports.BaseOutput] = None
        self.midi_in: Optional[mido.ports.BaseInput] = None

        # Threads
        self.output_thread: Optional[Thread] = None
        self.input_thread: Optional[Thread] = None

        # Queue for messages to send out
        self.send_queue = ThreadSafeQueue()

    def _find_matching_input_port(self, input_ports: List[str]) -> Optional[str]:
        """
        Find matching input port for the configured output port.

        mido/rtmidi appends different index numbers to input/output ports,
        so "loopMIDI Port 2" (output) might be "loopMIDI Port 1" (input).

        Args:
            input_ports: List of available input port names

        Returns:
            Matching input port name, or None if not found
        """
        # Strip trailing space + number from port name to get base name
        # "loopMIDI Port 2" -> "loopMIDI Port"
        import re
        base_name = re.sub(r'\s+\d+$', '', self.port_name)

        # Find input port that starts with the base name
        for port in input_ports:
            if port.startswith(base_name):
                if self.debug:
                    print(f"[MIDI] Matched input port: '{port}' for output port: '{self.port_name}'")
                return port

        return None

    def start(self):
        """
        Connect to loopMIDI port and start send/receive threads.

        Raises:
            RuntimeError: If MIDI port cannot be connected
        """
        try:
            # List available ports for debugging
            output_ports = mido.get_output_names()
            input_ports = mido.get_input_names()

            if self.debug:
                print(f"[MIDI] Available output ports: {output_ports}")
                print(f"[MIDI] Available input ports: {input_ports}")

            # Check if port exists in outputs
            if self.port_name not in output_ports:
                raise ValueError(
                    f"MIDI port '{self.port_name}' not found.\n\n"
                    f"Available ports: {', '.join(output_ports) if output_ports else 'None'}\n\n"
                    "Windows Setup Instructions:\n"
                    "1. Download loopMIDI: https://www.tobias-erichsen.de/software/loopmidi.html\n"
                    "2. Install and launch loopMIDI\n"
                    "3. Create a new port (e.g., 'loopMIDI Port')\n"
                    "4. Run: fucka config\n"
                    "5. Go to General Settings > Configure MIDI Port\n"
                    "6. Select your loopMIDI port from the list"
                )

            # Find matching input port (may have different index number than output)
            # Example: "loopMIDI Port 2" (output) -> "loopMIDI Port 1" (input)
            input_port_name = self._find_matching_input_port(input_ports)

            if not input_port_name:
                raise ValueError(
                    f"No matching input port found for '{self.port_name}'.\n\n"
                    f"Available input ports: {', '.join(input_ports) if input_ports else 'None'}\n\n"
                    "Make sure loopMIDI is running and the port is created."
                )

            # Connect to separate output and input ports
            self.midi_out = mido.open_output(self.port_name)
            self.midi_in = mido.open_input(input_port_name)

            if self.debug:
                print(f"[MIDI] Connected - Output: '{self.port_name}', Input: '{input_port_name}'")

            # Start output thread (sends MIDI from queue)
            self.output_thread = Thread(
                target=self._output_worker,
                daemon=True,
                name="MIDIOutput"
            )
            self.output_thread.start()

            # Start input thread (receives MIDI and forwards to overlay)
            self.input_thread = Thread(
                target=self._input_worker,
                daemon=True,
                name="MIDIInput"
            )
            self.input_thread.start()

            if self.debug:
                print("[MIDI] Started MIDI threads")

        except Exception as e:
            raise RuntimeError(f"Failed to connect to MIDI port: {e}")

    def stop(self):
        """
        Stop MIDI threads and close ports.
        """
        if self.debug:
            print("[MIDI] Stopping MIDI handler...")

        # Wait for threads to finish
        if self.output_thread and self.output_thread.is_alive():
            self.output_thread.join(timeout=2.0)

        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=2.0)

        # Close MIDI ports
        if self.midi_out:
            try:
                self.midi_out.close()
            except:
                pass

        if self.midi_in:
            try:
                self.midi_in.close()
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

        Converts raw byte message to mido Message object.

        Args:
            message: MIDI message as list of integers (status byte + data)
        """
        if self.midi_out is None:
            return

        try:
            # Convert raw bytes to mido Message
            status = message[0]
            msg_type = (status & 0xF0) >> 4
            channel = (status & 0x0F)

            if msg_type == 0x9:  # Note On
                msg = mido.Message('note_on',
                                  note=message[1],
                                  velocity=message[2],
                                  channel=channel)
            elif msg_type == 0x8:  # Note Off
                msg = mido.Message('note_off',
                                  note=message[1],
                                  velocity=message[2],
                                  channel=channel)
            elif msg_type == 0xB:  # Control Change
                msg = mido.Message('control_change',
                                  control=message[1],
                                  value=message[2],
                                  channel=channel)
            else:
                if self.debug:
                    print(f"[MIDI] Unknown message type: {hex(msg_type)}")
                return

            # Send via mido
            self.midi_out.send(msg)

            if self.debug:
                msg_type_str, channel_num, data1, data2 = parse_midi_message(message)
                print(f"[MIDI] Sent: {msg_type_str} CH{channel_num} D1:{data1} D2:{data2}")

        except Exception as e:
            if self.debug:
                print(f"[MIDI] Error sending message: {e}")

    def _input_worker(self):
        """
        Worker thread that receives MIDI messages.

        Polls for incoming messages and forwards them to overlay queue.
        Runs until shutdown_event is set.
        """
        if self.debug:
            print("[MIDI] Input worker started")

        while not self.shutdown_event.is_set():
            try:
                # Poll for incoming messages
                for msg in self.midi_in.iter_pending():
                    if msg.type == 'note_on':
                        midi_event = {
                            'type': 'note_on',
                            'channel': msg.channel,
                            'data1': msg.note,
                            'data2': msg.velocity
                        }
                        self.midi_to_overlay_queue.put(midi_event)

                        if self.debug:
                            print(f"[MIDI] Received: note_on CH{msg.channel} Note:{msg.note} Vel:{msg.velocity}")

                    elif msg.type == 'note_off':
                        midi_event = {
                            'type': 'note_off',
                            'channel': msg.channel,
                            'data1': msg.note,
                            'data2': msg.velocity
                        }
                        self.midi_to_overlay_queue.put(midi_event)

                        if self.debug:
                            print(f"[MIDI] Received: note_off CH{msg.channel} Note:{msg.note} Vel:{msg.velocity}")

                    elif msg.type == 'control_change':
                        midi_event = {
                            'type': 'cc',
                            'channel': msg.channel,
                            'data1': msg.control,
                            'data2': msg.value
                        }
                        self.midi_to_overlay_queue.put(midi_event)

                        if self.debug:
                            print(f"[MIDI] Received: cc CH{msg.channel} CC:{msg.control} Val:{msg.value}")

                # Small delay to prevent busy-waiting
                time.sleep(0.001)

            except Exception as e:
                if self.debug:
                    print(f"[MIDI] Error receiving message: {e}")
                time.sleep(0.01)

        if self.debug:
            print("[MIDI] Input worker stopped")

    def is_running(self) -> bool:
        """
        Check if MIDI handler is running.

        Returns:
            True if ports are open and threads are running
        """
        return (
            self.midi_out is not None and
            self.midi_in is not None and
            self.output_thread is not None and
            self.output_thread.is_alive() and
            self.input_thread is not None and
            self.input_thread.is_alive()
        )
