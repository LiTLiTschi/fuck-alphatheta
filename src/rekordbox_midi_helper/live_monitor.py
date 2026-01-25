"""
Live MIDI Monitor - Shows real-time color matching status.

Displays current pixel colors vs target colors for all configured monitors,
updating in real-time to help debug and verify monitor configurations.
"""

import time
import sys
import mss
import numpy as np
from typing import Dict, Any, List, Tuple
from colorama import init, Fore, Style

from .config_loader import ConfigLoader
from .utils.color_utils import color_matches

# Initialize colorama
init(autoreset=True)


class LiveMonitor:
    """
    Live monitor display for screen color matching.

    Shows real-time updates of:
    - Current pixel color vs target color
    - Match status (MATCH/NO MATCH)
    - Position coordinates
    """

    def __init__(self, config_path: str):
        """
        Initialize live monitor.

        Args:
            config_path: Path to configuration file
        """
        self.config = ConfigLoader(config_path)
        self.sct = None

    def run(self):
        """Run the live monitor display."""
        monitors = self.config.get_screen_monitors()

        if not monitors:
            print(f"{Fore.YELLOW}⚠ No monitors configured{Style.RESET_ALL}")
            print(f"{Fore.CYAN}ℹ Run 'fucka config' to set up monitors{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}✓ Live Monitor Started{Style.RESET_ALL}")
        print(f"{Fore.CYAN}ℹ Monitoring {len(monitors)} screen pixel(s){Style.RESET_ALL}")
        print(f"{Fore.CYAN}ℹ Press Ctrl+C to stop{Style.RESET_ALL}")
        print()

        try:
            with mss.mss() as self.sct:
                while True:
                    # Clear screen
                    print("\033[2J\033[H", end="")

                    # Header
                    print("=" * 100)
                    print(f"{Fore.CYAN}{'Live MIDI Monitor':^100}{Style.RESET_ALL}")
                    print("=" * 100)
                    print()

                    # Show each monitor
                    for monitor in monitors:
                        self._display_monitor(monitor)

                    print("=" * 100)
                    print(f"{Fore.YELLOW}Press Ctrl+C to stop{Style.RESET_ALL}")

                    # Update rate
                    time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n")
            print(f"{Fore.GREEN}✓ Live Monitor stopped{Style.RESET_ALL}")

    def _display_monitor(self, monitor: Dict[str, Any]):
        """
        Display current status of a single monitor.

        Args:
            monitor: Monitor configuration dictionary
        """
        monitor_id = monitor['id']
        position = monitor['position']
        target_color = monitor['target_color']
        tolerance = monitor['tolerance']
        midi_output = monitor['midi_output']

        # Get position
        x, y = position['x'], position['y']

        # Capture current color
        current_color = self._capture_color_at_position(x, y)
        if current_color is None:
            current_color = (0, 0, 0)

        # Target color
        target_rgb = (target_color['r'], target_color['g'], target_color['b'])

        # Check if matches
        matches = color_matches(current_color, target_rgb, tolerance)

        # Format output
        match_str = f"{Fore.GREEN}MATCH{Style.RESET_ALL}" if matches else f"{Fore.YELLOW}NO MATCH{Style.RESET_ALL}"

        # MIDI info
        if midi_output['type'] == 'note':
            midi_str = f"Note {midi_output['note']} Ch {midi_output['channel']}"
        else:
            midi_str = f"CC {midi_output['controller']} Ch {midi_output['channel']}"

        # Display
        print(f"{Fore.CYAN}{monitor_id}:{Style.RESET_ALL}")
        print(f"  Position: ({x}, {y})")
        print(f"  Current:  RGB{current_color}")
        print(f"  Target:   RGB{target_rgb}")
        print(f"  Status:   {match_str}")
        print(f"  MIDI:     {midi_str}")
        print()

    def _capture_color_at_position(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Capture color at a specific screen position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            RGB tuple or None if capture fails
        """
        try:
            monitor = {"left": x, "top": y, "width": 1, "height": 1}
            screenshot = self.sct.grab(monitor)

            img = np.array(screenshot)

            # MSS numpy array is BGRA format, convert to RGB
            # CRITICAL: Convert to int to avoid numpy uint8 overflow
            rgb_color = (int(img[0, 0, 2]), int(img[0, 0, 1]), int(img[0, 0, 0]))

            return rgb_color
        except Exception as e:
            return None


def main(config_path: str):
    """
    Main entry point for live monitor.

    Args:
        config_path: Path to configuration file
    """
    monitor = LiveMonitor(config_path)
    monitor.run()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Usage: python -m rekordbox_midi_helper.live_monitor <config_path>")
        sys.exit(1)
