"""
Interactive CLI Configuration Tool for Rekordbox MIDI Helper

This tool provides an interactive wizard for configuring the application:
- Click on screen to capture coordinates and colors
- Listen to MIDI devices to capture MIDI mappings
- Interactively define screen regions and shapes
- Live preview and validation
- Generate config.yaml with guided setup

Usage:
    python configure.py
    python configure.py --config custom_config.yaml
    python configure.py --edit config/config.yaml
"""

import sys
import os
import time
import threading
import shutil
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import yaml

# Third-party imports
try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button
except ImportError:
    print("ERROR: pynput not installed. Run: pip install pynput")
    sys.exit(1)

import mss
import numpy as np
from colorama import init, Fore, Back, Style
import rtmidi

# Import project modules (relative imports within package)
from .utils.color_utils import rgb_to_hex, average_region_color
from .utils.midi_utils import parse_midi_message
from .config_loader import ConfigLoader, ConfigValidationError

# Initialize colorama for colored terminal output
init(autoreset=True)


class ConfigWizard:
    """
    Interactive configuration wizard for Rekordbox MIDI Helper.

    Guides users through setting up screen monitors, MIDI mappings,
    and overlay shapes with visual feedback and live capture tools.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration wizard.

        Args:
            config_path: Path to save configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {
            'general': {
                'virtual_midi_port_name': 'Rekordbox Helper',
                'screen_monitor_fps': 30,
                'debug_mode': False
            },
            'screen_monitors': [],
            'shapes': {
                'static': [],
                'animated': []
            }
        }

        # Mouse/keyboard state
        self.current_mouse_pos: Tuple[int, int] = (0, 0)
        self.captured_positions: List[Tuple[int, int]] = []
        self.capture_active = False
        self.listener_active = False

        # MIDI state
        self.midi_in: Optional[rtmidi.MidiIn] = None
        self.last_midi_message: Optional[Dict[str, Any]] = None
        self.midi_listening = False

        # Screen capture
        self.sct = mss.mss()

    def print_header(self, text: str):
        """Print a styled header that adapts to terminal width."""
        # Get terminal width, with fallback to 80
        try:
            width = shutil.get_terminal_size().columns
        except:
            width = 80

        # Use minimum width of 40, maximum of 120
        width = max(40, min(120, width))

        # Print header with dynamic width
        print(f"\n{Fore.CYAN}{'=' * width}")
        print(f"{Fore.CYAN}{text.center(width)}")
        print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}\n")

    def print_info(self, text: str):
        """Print info message."""
        print(f"{Fore.GREEN}ℹ {text}{Style.RESET_ALL}")

    def print_warning(self, text: str):
        """Print warning message."""
        print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

    def print_error(self, text: str):
        """Print error message."""
        print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

    def print_success(self, text: str):
        """Print success message."""
        print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

    def get_input(self, prompt: str, default: str = "") -> str:
        """Get user input with optional default."""
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            return user_input if user_input else default
        return input(f"{prompt}: ").strip()

    def get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Get yes/no input from user."""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} [{default_str}]: ").strip().lower()

        if not response:
            return default
        return response in ['y', 'yes']

    def capture_mouse_position(self) -> Tuple[int, int]:
        """
        Capture mouse position when user clicks.

        Returns:
            Tuple of (x, y) coordinates
        """
        self.print_info("Move your mouse to the desired position and click LEFT button")
        self.print_info("Press ESC to cancel")

        self.captured_positions = []
        self.capture_active = True

        def on_click(x, y, button, pressed):
            if not self.capture_active:
                return False

            if button == Button.left and pressed:
                self.captured_positions.append((x, y))
                self.capture_active = False
                return False

        def on_press(key):
            if key == keyboard.Key.esc:
                self.capture_active = False
                return False

        # Start mouse and keyboard listeners
        mouse_listener = mouse.Listener(on_click=on_click)
        keyboard_listener = keyboard.Listener(on_press=on_press)

        mouse_listener.start()
        keyboard_listener.start()

        # Show live mouse position
        print("\n", end='', flush=True)
        while self.capture_active:
            controller = mouse.Controller()
            x, y = controller.position
            print(f"\rCurrent position: X={x:4d}, Y={y:4d}", end='', flush=True)
            time.sleep(0.05)

        mouse_listener.stop()
        keyboard_listener.stop()

        print()  # New line after position display

        if self.captured_positions:
            x, y = self.captured_positions[0]
            self.print_success(f"Captured position: X={x}, Y={y}")
            return (x, y)
        else:
            self.print_warning("Capture cancelled")
            return (0, 0)

    def capture_screen_region(self) -> Dict[str, int]:
        """
        Capture a screen region by clicking two corners.

        Returns:
            Dictionary with x, y, width, height
        """
        self.print_info("Click TWO corners to define the region (top-left and bottom-right)")
        self.print_info("Press ESC to cancel")

        self.captured_positions = []
        self.capture_active = True
        click_count = 0

        def on_click(x, y, button, pressed):
            nonlocal click_count
            if not self.capture_active:
                return False

            if button == Button.left and pressed:
                self.captured_positions.append((x, y))
                click_count += 1
                print(f"\n{Fore.GREEN}✓ Corner {click_count} captured: ({x}, {y}){Style.RESET_ALL}")

                if click_count >= 2:
                    self.capture_active = False
                    return False

        def on_press(key):
            if key == keyboard.Key.esc:
                self.capture_active = False
                return False

        mouse_listener = mouse.Listener(on_click=on_click)
        keyboard_listener = keyboard.Listener(on_press=on_press)

        mouse_listener.start()
        keyboard_listener.start()

        # Show live mouse position
        print("\n", end='', flush=True)
        while self.capture_active:
            controller = mouse.Controller()
            x, y = controller.position
            print(f"\rCurrent position: X={x:4d}, Y={y:4d} | Corners captured: {click_count}/2", end='', flush=True)
            time.sleep(0.05)

        mouse_listener.stop()
        keyboard_listener.stop()

        print()  # New line

        if len(self.captured_positions) >= 2:
            x1, y1 = self.captured_positions[0]
            x2, y2 = self.captured_positions[1]

            # Calculate region (normalize to top-left corner)
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            region = {'x': x, 'y': y, 'width': width, 'height': height}
            self.print_success(f"Region: X={x}, Y={y}, Width={width}, Height={height}")
            return region
        else:
            self.print_warning("Region capture cancelled")
            return {'x': 0, 'y': 0, 'width': 50, 'height': 50}

    def capture_color_at_position(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Capture color at a specific screen position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            RGB tuple (r, g, b)
        """
        try:
            # Capture small region around position
            monitor = {
                "left": x - 2,
                "top": y - 2,
                "width": 5,
                "height": 5
            }

            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)

            # Convert BGRA to RGB
            rgb_img = img[:, :, [2, 1, 0]]

            # Get average color
            avg_color = average_region_color(rgb_img)

            return avg_color
        except Exception as e:
            self.print_error(f"Failed to capture color: {e}")
            return (0, 0, 0)

    def capture_color_from_screen(self) -> Tuple[int, int, int]:
        """
        Interactively capture color by clicking on screen.

        Returns:
            RGB tuple (r, g, b)
        """
        self.print_info("Click on the screen location to capture its color")
        self.print_info("Press ESC to cancel")

        pos = self.capture_mouse_position()

        if pos != (0, 0):
            color = self.capture_color_at_position(pos[0], pos[1])
            hex_color = rgb_to_hex(color)

            # Show color preview
            print(f"\n{Fore.GREEN}Captured Color:{Style.RESET_ALL}")
            print(f"  RGB: ({color[0]}, {color[1]}, {color[2]})")
            print(f"  Hex: {hex_color}")

            # Try to show colored block (may not work in all terminals)
            print(f"  Preview: {Back.BLACK}  {Style.RESET_ALL} ← Color sample")

            return color

        return (0, 0, 0)

    def listen_for_midi(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """
        Listen for incoming MIDI messages.

        Args:
            timeout: Seconds to listen before timing out

        Returns:
            MIDI message dict or None if timeout/cancelled
        """
        self.print_info(f"Listening for MIDI input ({timeout}s timeout)...")
        self.print_info("Send a MIDI message from your controller or Bome")
        self.print_info("Press ESC to cancel")

        try:
            # Open MIDI input
            if self.midi_in is None:
                self.midi_in = rtmidi.MidiIn()

            # List available MIDI ports
            ports = self.midi_in.get_ports()

            if not ports:
                self.print_warning("No MIDI input ports found!")
                return None

            print(f"\n{Fore.CYAN}Available MIDI ports:{Style.RESET_ALL}")
            for i, port in enumerate(ports):
                print(f"  {i+1}. {port}")

            # Let user select port
            port_num = int(self.get_input(f"\nSelect port (1-{len(ports)})", "1"))

            if port_num < 1 or port_num > len(ports):
                self.print_error("Invalid port number")
                return None

            # Open the selected port
            self.midi_in.open_port(port_num - 1)

            self.last_midi_message = None
            self.midi_listening = True

            def midi_callback(event, data=None):
                message, delta_time = event
                msg_type, channel, data1, data2 = parse_midi_message(message)

                if msg_type != 'unknown':
                    self.last_midi_message = {
                        'type': msg_type,
                        'channel': channel,
                        'data1': data1,
                        'data2': data2
                    }
                    self.midi_listening = False

            self.midi_in.set_callback(midi_callback)

            # Wait for MIDI message or timeout
            start_time = time.time()

            def on_press(key):
                if key == keyboard.Key.esc:
                    self.midi_listening = False
                    return False

            keyboard_listener = keyboard.Listener(on_press=on_press)
            keyboard_listener.start()

            while self.midi_listening and (time.time() - start_time) < timeout:
                remaining = int(timeout - (time.time() - start_time))
                print(f"\rWaiting for MIDI... {remaining}s remaining", end='', flush=True)
                time.sleep(0.1)

            keyboard_listener.stop()
            print()  # New line

            # Close MIDI port
            self.midi_in.close_port()

            if self.last_midi_message:
                msg = self.last_midi_message
                self.print_success(f"Captured MIDI: {msg['type']} on channel {msg['channel']}")
                print(f"  Data1 (Note/Controller): {msg['data1']}")
                print(f"  Data2 (Velocity/Value): {msg['data2']}")
                return self.last_midi_message
            else:
                self.print_warning("No MIDI message received")
                return None

        except Exception as e:
            self.print_error(f"MIDI listening failed: {e}")
            return None

    def configure_general_settings(self):
        """Configure general application settings."""
        self.print_header("General Settings")

        self.config['general']['virtual_midi_port_name'] = self.get_input(
            "Virtual MIDI port name",
            self.config['general']['virtual_midi_port_name']
        )

        fps_str = self.get_input(
            "Screen monitor FPS (10-60)",
            str(self.config['general']['screen_monitor_fps'])
        )
        self.config['general']['screen_monitor_fps'] = int(fps_str)

        self.config['general']['debug_mode'] = self.get_yes_no(
            "Enable debug mode?",
            self.config['general']['debug_mode']
        )

    def configure_screen_monitor(self) -> Dict[str, Any]:
        """
        Configure a single screen monitor.

        Returns:
            Screen monitor configuration dict
        """
        self.print_header("Configure Screen Monitor")

        monitor_id = self.get_input("Monitor ID (e.g., 'deck_a_playing')")

        # Capture region
        print(f"\n{Fore.CYAN}Define screen region to monitor:{Style.RESET_ALL}")
        if self.get_yes_no("Capture region by clicking two corners?", True):
            region = self.capture_screen_region()
        else:
            region = {
                'x': int(self.get_input("X position", "100")),
                'y': int(self.get_input("Y position", "100")),
                'width': int(self.get_input("Width", "50")),
                'height': int(self.get_input("Height", "50"))
            }

        # Capture target color
        print(f"\n{Fore.CYAN}Define target color to detect:{Style.RESET_ALL}")
        if self.get_yes_no("Capture color from screen?", True):
            target_color = self.capture_color_from_screen()
            color_dict = {'r': target_color[0], 'g': target_color[1], 'b': target_color[2]}
        else:
            color_dict = {
                'r': int(self.get_input("Red (0-255)", "255")),
                'g': int(self.get_input("Green (0-255)", "0")),
                'b': int(self.get_input("Blue (0-255)", "0"))
            }

        tolerance = int(self.get_input("Color tolerance (0-50, higher = less strict)", "10"))

        # MIDI output configuration
        print(f"\n{Fore.CYAN}Configure MIDI output:{Style.RESET_ALL}")
        midi_type = self.get_input("MIDI type (note/cc)", "note").lower()

        if self.get_yes_no("Listen for MIDI to capture settings?", True):
            midi_msg = self.listen_for_midi()
            if midi_msg:
                channel = midi_msg['channel']
                if midi_type == 'note':
                    note = midi_msg['data1']
                    velocity_on = 127
                    velocity_off = 0
                else:  # cc
                    controller = midi_msg['data1']
                    value_match = 127
                    value_nomatch = 0
            else:
                # Manual input
                channel = int(self.get_input("MIDI channel (1-16)", "1"))
                if midi_type == 'note':
                    note = int(self.get_input("Note number (0-127)", "60"))
                    velocity_on = int(self.get_input("Velocity when matched (0-127)", "127"))
                    velocity_off = int(self.get_input("Velocity when not matched (0-127)", "0"))
                else:
                    controller = int(self.get_input("CC controller (0-127)", "20"))
                    value_match = int(self.get_input("Value when matched (0-127)", "127"))
                    value_nomatch = int(self.get_input("Value when not matched (0-127)", "0"))
        else:
            channel = int(self.get_input("MIDI channel (1-16)", "1"))
            if midi_type == 'note':
                note = int(self.get_input("Note number (0-127)", "60"))
                velocity_on = int(self.get_input("Velocity when matched (0-127)", "127"))
                velocity_off = int(self.get_input("Velocity when not matched (0-127)", "0"))
            else:
                controller = int(self.get_input("CC controller (0-127)", "20"))
                value_match = int(self.get_input("Value when matched (0-127)", "127"))
                value_nomatch = int(self.get_input("Value when not matched (0-127)", "0"))

        # Build MIDI output config
        midi_output = {
            'type': midi_type,
            'channel': channel
        }

        if midi_type == 'note':
            midi_output['note'] = note
            midi_output['velocity_on'] = velocity_on
            midi_output['velocity_off'] = velocity_off
        else:
            midi_output['controller'] = controller
            midi_output['value_match'] = value_match
            midi_output['value_nomatch'] = value_nomatch

        monitor_config = {
            'id': monitor_id,
            'region': region,
            'target_color': color_dict,
            'tolerance': tolerance,
            'midi_output': midi_output
        }

        self.print_success(f"Screen monitor '{monitor_id}' configured!")
        return monitor_config

    def configure_static_shape(self) -> Dict[str, Any]:
        """
        Configure a static shape.

        Returns:
            Static shape configuration dict
        """
        self.print_header("Configure Static Shape")

        shape_id = self.get_input("Shape ID (e.g., 'deck_a_indicator')")
        shape_type = self.get_input("Shape type (circle/rectangle)", "circle").lower()

        # Position
        print(f"\n{Fore.CYAN}Define shape position:{Style.RESET_ALL}")
        if self.get_yes_no("Click to set position?", True):
            pos = self.capture_mouse_position()
            position = {'x': pos[0], 'y': pos[1]}
        else:
            position = {
                'x': int(self.get_input("X position", "100")),
                'y': int(self.get_input("Y position", "100"))
            }

        # Size
        if shape_type == 'circle':
            radius = int(self.get_input("Radius (pixels)", "30"))
            size = {'radius': radius}
        else:
            width = int(self.get_input("Width (pixels)", "60"))
            height = int(self.get_input("Height (pixels)", "60"))
            size = {'width': width, 'height': height}

        # Color
        color = {
            'r': int(self.get_input("Red (0-255)", "255")),
            'g': int(self.get_input("Green (0-255)", "0")),
            'b': int(self.get_input("Blue (0-255)", "0")),
            'a': int(self.get_input("Alpha/Opacity (0-255)", "200"))
        }

        # MIDI trigger
        print(f"\n{Fore.CYAN}Configure MIDI trigger:{Style.RESET_ALL}")
        if self.get_yes_no("Listen for MIDI to capture trigger?", True):
            midi_msg = self.listen_for_midi()
            if midi_msg:
                trigger_midi = {
                    'type': midi_msg['type'],
                    'channel': midi_msg['channel'],
                    'note': midi_msg['data1']
                }
            else:
                trigger_midi = {
                    'type': 'note',
                    'channel': 1,
                    'note': 60
                }
        else:
            trigger_midi = {
                'type': self.get_input("Trigger type (note/cc)", "note"),
                'channel': int(self.get_input("MIDI channel (1-16)", "1")),
                'note': int(self.get_input("Note number (0-127)", "60"))
            }

        shape_config = {
            'id': shape_id,
            'type': shape_type,
            'position': position,
            'size': size,
            'color': color,
            'trigger_midi': trigger_midi
        }

        self.print_success(f"Static shape '{shape_id}' configured!")
        return shape_config

    def configure_animated_shape(self) -> Dict[str, Any]:
        """
        Configure an animated shape.

        Returns:
            Animated shape configuration dict
        """
        self.print_header("Configure Animated Shape")

        shape_id = self.get_input("Shape ID (e.g., 'crossfader_pie')")
        shape_type = self.get_input("Shape type (pie_chart/progress_bar)", "pie_chart").lower()

        # Position
        print(f"\n{Fore.CYAN}Define shape position:{Style.RESET_ALL}")
        if self.get_yes_no("Click to set position?", True):
            pos = self.capture_mouse_position()
            position = {'x': pos[0], 'y': pos[1]}
        else:
            position = {
                'x': int(self.get_input("X position", "500")),
                'y': int(self.get_input("Y position", "300"))
            }

        # Size
        if shape_type == 'pie_chart':
            radius = int(self.get_input("Radius (pixels)", "50"))
            size = {'radius': radius}
        else:
            width = int(self.get_input("Width (pixels)", "200"))
            height = int(self.get_input("Height (pixels)", "20"))
            size = {'width': width, 'height': height}

        # Color
        color = {
            'r': int(self.get_input("Red (0-255)", "0")),
            'g': int(self.get_input("Green (0-255)", "150")),
            'b': int(self.get_input("Blue (0-255)", "255")),
            'a': int(self.get_input("Alpha/Opacity (0-255)", "180"))
        }

        # MIDI control
        print(f"\n{Fore.CYAN}Configure MIDI CC control:{Style.RESET_ALL}")
        if self.get_yes_no("Listen for MIDI CC to capture controller?", True):
            self.print_info("Move a fader or knob on your controller to send CC")
            midi_msg = self.listen_for_midi()
            if midi_msg:
                control_midi = {
                    'type': 'cc',
                    'channel': midi_msg['channel'],
                    'controller': midi_msg['data1']
                }
            else:
                control_midi = {
                    'type': 'cc',
                    'channel': 1,
                    'controller': 10
                }
        else:
            control_midi = {
                'type': 'cc',
                'channel': int(self.get_input("MIDI channel (1-16)", "1")),
                'controller': int(self.get_input("CC controller (0-127)", "10"))
            }

        # Animation parameters
        if shape_type == 'pie_chart':
            animation = {
                'start_angle': int(self.get_input("Start angle (degrees)", "0")),
                'end_angle_range': [0, 360],
                'fill_direction': self.get_input("Fill direction (clockwise/counterclockwise)", "clockwise")
            }
        else:  # progress_bar
            animation = {
                'direction': self.get_input("Direction (horizontal/vertical)", "horizontal"),
                'fill_direction': self.get_input("Fill direction (left_to_right/right_to_left/top_to_bottom/bottom_to_top)", "left_to_right")
            }

        shape_config = {
            'id': shape_id,
            'type': shape_type,
            'position': position,
            'size': size,
            'color': color,
            'control_midi': control_midi,
            'animation': animation
        }

        self.print_success(f"Animated shape '{shape_id}' configured!")
        return shape_config

    def save_config(self):
        """Save configuration to YAML file."""
        try:
            # Create config directory if it doesn't exist
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # Create backup if file exists
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.backup"
                import shutil
                shutil.copy2(self.config_path, backup_path)
                self.print_info(f"Created backup: {backup_path}")

            # Write YAML file
            with open(self.config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

            self.print_success(f"Configuration saved to: {self.config_path}")

            # Validate
            try:
                ConfigLoader(self.config_path)
                self.print_success("Configuration validated successfully!")
            except ConfigValidationError as e:
                self.print_error(f"Configuration validation failed: {e}")

        except Exception as e:
            self.print_error(f"Failed to save configuration: {e}")

    def run(self):
        """Run the interactive configuration wizard."""
        self.print_header("Rekordbox MIDI Helper - Configuration Wizard")

        print("This wizard will help you configure:")
        print("  • General settings")
        print("  • Screen monitoring regions")
        print("  • Overlay shapes")
        print("  • MIDI mappings")
        print()

        try:
            # General settings
            self.configure_general_settings()

            # Screen monitors
            if self.get_yes_no("\nConfigure screen monitors?", True):
                while True:
                    monitor = self.configure_screen_monitor()
                    self.config['screen_monitors'].append(monitor)

                    if not self.get_yes_no("\nAdd another screen monitor?", False):
                        break

            # Static shapes
            if self.get_yes_no("\nConfigure static shapes?", True):
                while True:
                    shape = self.configure_static_shape()
                    self.config['shapes']['static'].append(shape)

                    if not self.get_yes_no("\nAdd another static shape?", False):
                        break

            # Animated shapes
            if self.get_yes_no("\nConfigure animated shapes?", True):
                while True:
                    shape = self.configure_animated_shape()
                    self.config['shapes']['animated'].append(shape)

                    if not self.get_yes_no("\nAdd another animated shape?", False):
                        break

            # Save configuration
            # Get terminal width for summary box
            try:
                width = shutil.get_terminal_size().columns
            except:
                width = 80
            width = max(40, min(120, width))

            print("\n" + "=" * width)
            print("Configuration Summary:".center(width))
            print("=" * width)
            print(f"Screen monitors: {len(self.config['screen_monitors'])}")
            print(f"Static shapes: {len(self.config['shapes']['static'])}")
            print(f"Animated shapes: {len(self.config['shapes']['animated'])}")
            print()

            if self.get_yes_no("Save configuration?", True):
                self.save_config()
                print()
                self.print_success("Configuration complete!")
                print(f"\nTo run the application:")
                print(f"  python src/main.py --config {self.config_path}")
            else:
                self.print_warning("Configuration not saved")

        except KeyboardInterrupt:
            print("\n\n")
            self.print_warning("Configuration wizard cancelled")
        except Exception as e:
            print("\n\n")
            self.print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point for configuration wizard."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive configuration wizard for Rekordbox MIDI Helper"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to save configuration file (default: config/config.yaml)'
    )
    parser.add_argument(
        '--edit',
        type=str,
        help='Edit existing configuration file'
    )

    args = parser.parse_args()

    config_path = args.edit if args.edit else args.config

    wizard = ConfigWizard(config_path)
    wizard.run()


if __name__ == '__main__':
    main()
