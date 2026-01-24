"""
Rekordbox MIDI Helper - Main Application Entry Point

This application enhances Rekordbox usability with Bome MIDI Translator Pro by:
1. Monitoring screen pixels for color changes and sending MIDI messages
2. Drawing transparent overlay shapes controlled by MIDI input
3. Supporting animated shapes (pie charts, progress bars) via MIDI CC

Usage:
    python main.py [--config path/to/config.yaml] [--debug]

Architecture:
- Main thread: Qt event loop for overlay window
- Thread 1: Screen monitoring (captures regions, detects colors)
- Thread 2: MIDI output (sends messages from screen monitor)
- Thread 3: MIDI input (receives messages via callback)

Author: Created out of frustration with AlphaTheta's hardware limitations
"""

import sys
import os
import argparse
import signal
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Import project modules (relative imports within package)
from .config_loader import ConfigLoader, ConfigValidationError
from .screen_monitor import ScreenMonitor
from .midi_handler import MIDIHandler
from .overlay_window import OverlayWindow
from .utils.threading_utils import ThreadSafeQueue, ShutdownEvent
from .utils.config_path import get_config_path


class RekordboxMIDIHelper:
    """
    Main application class that orchestrates all components.

    Manages:
    - Configuration loading
    - Thread lifecycle
    - MIDI handler
    - Overlay window
    - Graceful shutdown
    """

    def __init__(self, config_path: str, debug: bool = False):
        """
        Initialize application.

        Args:
            config_path: Path to YAML configuration file
            debug: Enable debug logging
        """
        self.config_path = config_path
        self.debug = debug

        # Load configuration
        try:
            self.config = ConfigLoader(config_path)
            if self.debug:
                print(f"[Main] Loaded configuration from {config_path}")
        except (FileNotFoundError, ConfigValidationError) as e:
            print(f"ERROR: Configuration failed: {e}")
            print("\nPlease run 'fucka config' to create a configuration file")
            sys.exit(1)

        # Threading components
        self.shutdown_event = ShutdownEvent()

        # Queues for inter-thread communication
        self.screen_to_midi_queue = ThreadSafeQueue()  # Screen monitor -> MIDI out
        self.midi_to_overlay_queue = ThreadSafeQueue()  # MIDI in -> Overlay

        # Component instances
        self.screen_monitor = None
        self.midi_handler = None
        self.overlay_window = None
        self.app = None

    def run(self):
        """
        Start the application.

        Creates Qt application, starts threads, and enters event loop.
        """
        # Create Qt application
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Rekordbox MIDI Helper")

        if self.debug:
            print("[Main] Qt application created")

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Allow Ctrl+C to work with Qt
        timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(500)

        try:
            # Start MIDI handler
            self._start_midi_handler()

            # Start screen monitor thread
            self._start_screen_monitor()

            # Create overlay window
            self._create_overlay_window()

            if self.debug:
                print("[Main] All components started")
                print("[Main] Press Ctrl+C to exit")

            # Enter Qt event loop
            exit_code = self.app.exec_()

            # Clean shutdown
            self.shutdown()

            sys.exit(exit_code)

        except Exception as e:
            print(f"ERROR: Application failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            self.shutdown()
            sys.exit(1)

    def _start_midi_handler(self):
        """Start MIDI handler for virtual port communication."""
        port_name = self.config.get_midi_port_name()

        try:
            self.midi_handler = MIDIHandler(
                port_name=port_name,
                midi_to_overlay_queue=self.midi_to_overlay_queue,
                shutdown_event=self.shutdown_event,
                debug=self.debug
            )
            self.midi_handler.start()

            if self.debug:
                print(f"[Main] MIDI handler started with port '{port_name}'")

        except RuntimeError as e:
            print(f"ERROR: Failed to start MIDI handler: {e}")
            raise

    def _start_screen_monitor(self):
        """Start screen monitoring thread."""
        monitors_config = self.config.get_screen_monitors()

        if not monitors_config:
            if self.debug:
                print("[Main] No screen monitors configured, skipping")
            return

        fps = self.config.get_screen_monitor_fps()

        self.screen_monitor = ScreenMonitor(
            monitors_config=monitors_config,
            midi_output_queue=self.screen_to_midi_queue,
            shutdown_event=self.shutdown_event,
            fps=fps,
            debug=self.debug
        )
        self.screen_monitor.start()

        # Connect screen monitor output to MIDI sender
        # We need a timer to periodically check the queue
        self.screen_monitor_timer = QTimer()
        self.screen_monitor_timer.timeout.connect(self._process_screen_monitor_queue)
        self.screen_monitor_timer.start(10)  # Check every 10ms

        if self.debug:
            print(f"[Main] Screen monitor started ({len(monitors_config)} regions, {fps} FPS)")

    def _process_screen_monitor_queue(self):
        """Process screen monitor events and send MIDI messages."""
        events = self.screen_to_midi_queue.get_all()

        for event in events:
            if self.midi_handler:
                self.midi_handler.send_from_screen_monitor(event)

    def _create_overlay_window(self):
        """Create transparent overlay window."""
        shapes_config = self.config.get_shapes()

        self.overlay_window = OverlayWindow(
            shapes_config=shapes_config,
            midi_input_queue=self.midi_to_overlay_queue,
            debug=self.debug
        )

        static_count, animated_count = self.overlay_window.get_shape_count()
        if self.debug:
            print(f"[Main] Overlay window created ({static_count} static, {animated_count} animated shapes)")

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (Ctrl+C, etc.)

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        print("\n[Main] Shutdown signal received, exiting gracefully...")
        self.shutdown()
        sys.exit(0)

    def shutdown(self):
        """
        Gracefully shutdown all components.

        Stops threads, closes MIDI ports, and cleans up resources.
        """
        if self.debug:
            print("[Main] Shutting down...")

        # Signal all threads to stop
        self.shutdown_event.set()

        # Stop screen monitor
        if self.screen_monitor:
            self.screen_monitor.join(timeout=2.0)
            if self.debug:
                print("[Main] Screen monitor stopped")

        # Stop MIDI handler
        if self.midi_handler:
            self.midi_handler.stop()
            if self.debug:
                print("[Main] MIDI handler stopped")

        # Close overlay window
        if self.overlay_window:
            self.overlay_window.close()
            if self.debug:
                print("[Main] Overlay window closed")

        if self.debug:
            print("[Main] Shutdown complete")


def main():
    """
    Main entry point for the application.

    Parses command line arguments and starts the application.
    """
    # Get default config path
    default_config = str(get_config_path())

    parser = argparse.ArgumentParser(
        description="Rekordbox MIDI Helper - Screen monitoring and overlay for DJ controllers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --config custom_config.yaml
  python main.py --debug

For more information, see README.md
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default=default_config,
        help=f'Path to configuration file (default: {default_config})'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Print banner
    print("=" * 60)
    print("Rekordbox MIDI Helper")
    print("Because AlphaTheta sucks and DJs deserve better")
    print("=" * 60)
    print()

    # Check if config exists
    if not os.path.exists(args.config):
        print(f"ERROR: Configuration file not found: {args.config}")
        print()
        print("Please run 'fucka config' to create a configuration file")
        sys.exit(1)

    # Create and run application
    app = RekordboxMIDIHelper(
        config_path=args.config,
        debug=args.debug
    )

    app.run()


if __name__ == '__main__':
    main()
