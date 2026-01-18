"""
Screen monitoring thread for detecting color changes at specific pixel positions.

This module captures single pixels using MSS and detects when colors match
configured targets. When a match is detected, MIDI events are queued for sending.

Threading: Runs in a separate thread to avoid blocking the UI
Performance: Achieves 30-100 FPS depending on configuration
Note: Monitors single pixels for optimal performance, not regions
"""

import mss
import numpy as np
from threading import Thread
from typing import Dict, List, Any, Tuple
import time

from .utils.color_utils import color_matches
from .utils.threading_utils import ThreadSafeQueue, ShutdownEvent, RateLimiter


class ScreenMonitor(Thread):
    """
    Thread that monitors screen pixels for color changes.

    Captures specified pixels at configurable FPS and detects when
    the color matches configured targets. Sends MIDI events when state changes.

    Supports both 'position' (new single-pixel format) and 'region' (old format)
    for backward compatibility.

    Example:
        monitor = ScreenMonitor(monitors_config, midi_queue, shutdown_event, fps=30)
        monitor.start()
        # ... do other work ...
        shutdown_event.set()
        monitor.join()
    """

    def __init__(self,
                 monitors_config: List[Dict[str, Any]],
                 midi_output_queue: ThreadSafeQueue,
                 shutdown_event: ShutdownEvent,
                 fps: int = 30,
                 debug: bool = False):
        """
        Initialize screen monitor thread.

        Args:
            monitors_config: List of monitor configurations from config file
            midi_output_queue: Queue to send MIDI events to
            shutdown_event: Event to signal thread shutdown
            fps: Target frames per second for monitoring
            debug: Enable debug logging
        """
        super().__init__(daemon=True, name="ScreenMonitor")

        self.monitors_config = monitors_config
        self.midi_output_queue = midi_output_queue
        self.shutdown_event = shutdown_event
        self.debug = debug

        # Rate limiting for FPS control
        self.rate_limiter = RateLimiter(fps)

        # MSS screen capture instance (created in thread)
        self.sct = None

        # Track state of each monitor to detect changes
        # Format: {monitor_id: bool} where True = color matched
        self.monitor_states: Dict[str, bool] = {}

        # Initialize states to False (no match)
        for monitor in self.monitors_config:
            self.monitor_states[monitor['id']] = False

    def run(self):
        """
        Main thread loop - captures screen and detects color changes.

        This runs in a separate thread until shutdown_event is set.
        """
        # Create MSS instance in this thread (not thread-safe to create in main)
        with mss.mss() as self.sct:
            if self.debug:
                print("[ScreenMonitor] Started monitoring")

            while not self.shutdown_event.is_set():
                # Rate limit to target FPS
                self.rate_limiter.wait_if_needed()

                # Check each configured monitor
                for monitor_config in self.monitors_config:
                    self._check_monitor(monitor_config)

            if self.debug:
                print("[ScreenMonitor] Stopped monitoring")

    def _check_monitor(self, monitor_config: Dict[str, Any]):
        """
        Check a single screen monitor for color match.

        Args:
            monitor_config: Configuration dictionary for this monitor
        """
        monitor_id = monitor_config['id']

        # Support both 'position' (new) and 'region' (old) formats
        if 'position' in monitor_config:
            position = monitor_config['position']
        elif 'region' in monitor_config:
            # Backward compatibility: extract x,y from old region format
            region = monitor_config['region']
            position = {'x': region['x'], 'y': region['y']}
        else:
            if self.debug:
                print(f"[ScreenMonitor] {monitor_id}: Missing position/region config")
            return

        target_color = monitor_config['target_color']
        tolerance = monitor_config['tolerance']
        midi_output = monitor_config['midi_output']

        # Capture pixel color
        captured_color = self._capture_pixel_color(position)

        if captured_color is None:
            return  # Capture failed

        # Check if color matches target
        target_rgb = (target_color['r'], target_color['g'], target_color['b'])
        matches = color_matches(captured_color, target_rgb, tolerance)

        # Get previous state
        previous_state = self.monitor_states[monitor_id]

        # Detect state change
        if matches != previous_state:
            self.monitor_states[monitor_id] = matches

            # Queue MIDI event for state change
            self._queue_midi_event(monitor_id, midi_output, matches)

            if self.debug:
                state_str = "MATCHED" if matches else "UNMATCHED"
                print(f"[ScreenMonitor] {monitor_id}: {state_str} - Color: {captured_color}")

    def _capture_pixel_color(self, position: Dict[str, int]) -> Tuple[int, int, int]:
        """
        Capture a single pixel and return its color.

        Args:
            position: Dictionary with x, y coordinates

        Returns:
            RGB tuple (r, g, b) or None if capture fails
        """
        try:
            # Define single pixel region for MSS
            monitor_region = {
                "left": position['x'],
                "top": position['y'],
                "width": 1,
                "height": 1
            }

            # Capture single pixel
            screenshot = self.sct.grab(monitor_region)

            # Convert to numpy array (BGRA format from MSS)
            img = np.array(screenshot)

            # MSS returns BGRA, convert to RGB
            # Get single pixel color (no averaging needed)
            # Format: img[y, x, channel] but for 1x1 it's img[0, 0, channel]
            rgb_color = (img[0, 0, 2], img[0, 0, 1], img[0, 0, 0])  # BGR to RGB

            return rgb_color

        except Exception as e:
            if self.debug:
                print(f"[ScreenMonitor] Error capturing pixel: {e}")
            return None

    def _capture_region_color(self, region: Dict[str, int]) -> Tuple[int, int, int]:
        """
        Capture a screen region and return its average color (DEPRECATED).

        This method is kept for backward compatibility with old configs.
        New code should use _capture_pixel_color instead.

        Args:
            region: Dictionary with x, y, width, height

        Returns:
            RGB tuple (r, g, b) or None if capture fails
        """
        try:
            # Define monitor region for MSS
            monitor_region = {
                "left": region['x'],
                "top": region['y'],
                "width": region.get('width', 1),
                "height": region.get('height', 1)
            }

            # Capture screen region
            screenshot = self.sct.grab(monitor_region)

            # Convert to numpy array (BGRA format from MSS)
            img = np.array(screenshot)

            # MSS returns BGRA, convert to RGB
            # Note: MSS uses BGR order, so we need to swap B and R
            rgb_img = img[:, :, [2, 1, 0]]  # BGR to RGB

            # Get average color of region (reduces noise)
            avg_color = average_region_color(rgb_img)

            return avg_color

        except Exception as e:
            if self.debug:
                print(f"[ScreenMonitor] Error capturing region: {e}")
            return None

    def _queue_midi_event(self, monitor_id: str, midi_output: Dict[str, Any], is_matched: bool):
        """
        Queue a MIDI event to send based on color match state.

        Args:
            monitor_id: ID of the monitor that changed state
            midi_output: MIDI output configuration
            is_matched: True if color matched, False otherwise
        """
        event = {
            'source': 'screen_monitor',
            'monitor_id': monitor_id,
            'matched': is_matched,
            'midi_config': midi_output
        }

        self.midi_output_queue.put(event)

    def get_current_states(self) -> Dict[str, bool]:
        """
        Get current state of all monitors.

        Returns:
            Dictionary of {monitor_id: is_matched}
        """
        return self.monitor_states.copy()
