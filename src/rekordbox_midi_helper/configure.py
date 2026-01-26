"""
Interactive Menu-Based Configuration Tool for Rekordbox MIDI Helper

This tool provides a complete menu-based UI for configuring the application:
- Full CRUD operations (Create, Read, Update, Delete) for all config items
- Single-pixel screen monitoring (not region-based)
- Click on screen to capture pixel positions and colors
- Listen to MIDI devices to capture MIDI mappings
- Hierarchical menu navigation with status bar
- Live testing and validation

Usage:
    fucka config
    fucka config --config custom_config.yaml
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

# Import project modules (relative imports within package)
from .utils.color_utils import rgb_to_hex
from .utils.midi_utils import parse_midi_message
from .utils.config_path import get_config_path
from .config_loader import ConfigLoader, ConfigValidationError

# Initialize colorama for colored terminal output
init(autoreset=True)


class ConfigMenu:
    """
    Menu-based configuration interface for Rekordbox MIDI Helper.

    Provides full CRUD operations for all configuration items through
    a hierarchical menu system with keyboard shortcuts and status tracking.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration menu.

        Args:
            config_path: Path to save/load configuration file (defaults to ~/.config/fucka/config.yaml)
        """
        self.config_path = config_path if config_path else str(get_config_path())

        # Menu state management
        self.menu_stack: List[str] = []  # Navigation breadcrumb
        self.unsaved_changes = False  # Track unsaved modifications

        # Load existing config or initialize default
        if os.path.exists(config_path):
            self.load_config()
        else:
            self.init_default_config()

        # Mouse/keyboard state
        self.current_mouse_pos: Tuple[int, int] = (0, 0)
        self.captured_positions: List[Tuple[int, int]] = []
        self.capture_active = False
        self.listener_active = False

        # MIDI state (for listen_for_midi)
        self.last_midi_message: Optional[Dict[str, Any]] = None

        # Screen capture
        self.sct = mss.mss()

        # Shape preview state
        self.shape_preview_window: Optional['ShapePreviewWindow'] = None
        self.preview_app: Optional['QApplication'] = None

    def init_default_config(self):
        """Initialize default configuration structure with presets."""
        self.config: Dict[str, Any] = {
            'general': {
                'midi_port': 'loopMIDI Port',
                'midi_input_port': '',
                'screen_monitor_fps': 30,
                'debug_mode': False,
                'active_preset': 'default'
            },
            'presets': {
                'default': {
                    'screen_monitors': [],
                    'shapes': {
                        'static': [],
                        'animated': []
                    }
                }
            }
        }

    def get_active_preset_name(self) -> str:
        """Get the name of the currently active preset."""
        return self.config.get('general', {}).get('active_preset', 'default')

    def get_active_preset(self) -> Dict[str, Any]:
        """Get the currently active preset configuration."""
        preset_name = self.get_active_preset_name()
        return self.config.get('presets', {}).get(preset_name, {
            'screen_monitors': [],
            'shapes': {'static': [], 'animated': []}
        })

    def get_preset_names(self) -> List[str]:
        """Get list of all preset names."""
        return list(self.config.get('presets', {}).keys())

    def set_active_preset(self, preset_name: str):
        """Set the active preset."""
        if preset_name in self.get_preset_names():
            self.config['general']['active_preset'] = preset_name
            self.has_unsaved_changes = True

    def load_config(self, path: Optional[str] = None):
        """
        Load configuration from YAML file with migration support.

        Args:
            path: Optional path to config file (uses self.config_path if not specified)
        """
        config_path = path or self.config_path

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            if config is None:
                self.init_default_config()
                return

            # Migrate old 'region' format to new 'position' format
            migrated = False
            if 'screen_monitors' in config:
                for monitor in config['screen_monitors']:
                    if 'region' in monitor and 'position' not in monitor:
                        # Convert old format: take x,y from region, discard width/height
                        region = monitor['region']
                        monitor['position'] = {
                            'x': region['x'],
                            'y': region['y']
                        }
                        del monitor['region']
                        migrated = True
                        self.print_warning(f"Migrated monitor '{monitor['id']}' to single-pixel format")

            self.config = config

            if migrated:
                self.unsaved_changes = True
                self.print_info("Config migrated from old format - remember to save!")

        except FileNotFoundError:
            self.print_warning(f"Config file not found: {config_path}")
            self.init_default_config()
        except Exception as e:
            self.print_error(f"Error loading config: {e}")
            self.init_default_config()

    def mark_unsaved(self):
        """Mark configuration as having unsaved changes."""
        self.unsaved_changes = True

    def mark_saved(self):
        """Mark configuration as saved."""
        self.unsaved_changes = False

    def get_breadcrumb(self) -> str:
        """
        Get current navigation path as breadcrumb string.

        Returns:
            Breadcrumb string like "Main Menu > Screen Monitors > Edit"
        """
        if not self.menu_stack:
            return "Main Menu"
        return "Main Menu > " + " > ".join(self.menu_stack)

    def print_status_bar(self):
        """Print status bar showing unsaved changes, current preset, and item counts."""
        # Get terminal width
        try:
            width = shutil.get_terminal_size().columns
        except:
            width = 80
        width = max(40, min(120, width))

        # Build status message
        if self.unsaved_changes:
            status = f"{Fore.YELLOW}Unsaved: Yes{Style.RESET_ALL}"
        else:
            status = f"{Fore.GREEN}All changes saved{Style.RESET_ALL}"

        # Get active preset
        preset_name = self.get_active_preset_name()
        preset = self.get_active_preset()

        # Count items from active preset
        monitor_count = len(preset.get('screen_monitors', []))
        static_count = len(preset.get('shapes', {}).get('static', []))
        animated_count = len(preset.get('shapes', {}).get('animated', []))
        total_shapes = static_count + animated_count

        # Format status line
        preset_display = f"{Fore.CYAN}Preset: {preset_name}{Style.RESET_ALL}"
        counts = f"Monitors: {monitor_count} | Shapes: {total_shapes}"

        status_line = f"[Status] {status} | {preset_display} | {counts}"

        # Print with padding
        print()
        print(status_line)

    def print_menu_header(self, title: str, show_breadcrumb: bool = True):
        """
        Print menu header with breadcrumb and horizontal line.

        Args:
            title: Menu title
            show_breadcrumb: Whether to show navigation path
        """
        # Get terminal width
        try:
            width = shutil.get_terminal_size().columns
        except:
            width = 80
        width = max(40, min(120, width))

        # Print header
        print(f"\n{Fore.CYAN}{'=' * width}")
        print(f"{Fore.CYAN}{title.center(width)}")
        print(f"{Fore.CYAN}{'=' * width}{Style.RESET_ALL}")

        # Print breadcrumb if requested
        if show_breadcrumb:
            breadcrumb = self.get_breadcrumb()
            print(f"{Fore.CYAN}Path: {breadcrumb}{Style.RESET_ALL}\n")
        else:
            print()

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

    def handle_global_commands(self, choice: str) -> Optional[str]:
        """
        Handle global menu commands available in all menus.

        Args:
            choice: User's input choice

        Returns:
            'exit' if should quit, 'saved' if saved, None if not a global command
        """
        if choice == 'q':
            if self.confirm_exit():
                return 'exit'
        elif choice == 's':
            self.save_config()
            return 'saved'
        return None

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

    def get_int_input(self, prompt: str, default: int, min_val: int = None, max_val: int = None) -> int:
        """
        Get integer input with validation and error handling.

        Args:
            prompt: Prompt message
            default: Default value
            min_val: Minimum acceptable value (optional)
            max_val: Maximum acceptable value (optional)

        Returns:
            Valid integer within range
        """
        while True:
            try:
                value_str = self.get_input(prompt, str(default))
                value = int(value_str)

                if min_val is not None and value < min_val:
                    self.print_error(f"Value must be at least {min_val}")
                    continue
                if max_val is not None and value > max_val:
                    self.print_error(f"Value must be at most {max_val}")
                    continue

                return value
            except ValueError:
                self.print_error(f"Invalid number: '{value_str}'. Please enter a valid integer.")

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

    def capture_screen_pixel(self) -> Dict[str, int]:
        """
        Capture single pixel position by clicking.

        Returns:
            Dictionary with x, y coordinates
        """
        self.print_info("Click on the pixel you want to monitor")
        pos = self.capture_mouse_position()

        return {
            'x': pos[0],
            'y': pos[1]
        }

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
            # Capture single pixel (1x1) - exactly like the working script
            monitor = {
                "left": x,
                "top": y,
                "width": 1,
                "height": 1
            }

            screenshot = self.sct.grab(monitor)

            # Use numpy array like screen_monitor.py (proven to work)
            img = np.array(screenshot)

            # MSS numpy array is BGRA format, convert to RGB
            # img[0, 0, 0] = B, img[0, 0, 1] = G, img[0, 0, 2] = R
            rgb_color = (int(img[0, 0, 2]), int(img[0, 0, 1]), int(img[0, 0, 0]))

            return rgb_color
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
            r, g, b = color
            print(f"  Preview: \033[48;2;{r};{g};{b}m    {Style.RESET_ALL} ← Color sample")

            return color

        return (0, 0, 0)

    def show_shape_preview(self, shape_config: Dict[str, Any]) -> None:
        """
        Show a live preview of the shape being configured.

        Args:
            shape_config: Shape configuration (id, type, position, size, color)
        """
        from PyQt5.QtWidgets import QApplication
        from .shape_preview import ShapePreviewWindow

        # Initialize Qt app if needed (but don't block terminal)
        if self.preview_app is None:
            self.preview_app = QApplication.instance()
            if self.preview_app is None:
                self.preview_app = QApplication([])

        # Close existing preview if any
        if self.shape_preview_window is not None:
            self.shape_preview_window.close()
            self.shape_preview_window = None

        # Create and show new preview
        self.shape_preview_window = ShapePreviewWindow(shape_config)
        self.shape_preview_window.show()

        # Process events to show window without blocking
        self.preview_app.processEvents()

        self.print_success("Shape preview is now visible on screen")

    def hide_shape_preview(self) -> None:
        """
        Hide and cleanup the shape preview window.
        """
        if self.shape_preview_window is not None:
            self.shape_preview_window.close()
            self.shape_preview_window = None

            # Process events to ensure cleanup
            if self.preview_app is not None:
                self.preview_app.processEvents()

            self.print_info("Shape preview closed")

    def update_shape_preview(self, shape_config: Dict[str, Any]) -> None:
        """
        Update the existing shape preview with new configuration.

        Args:
            shape_config: Updated shape configuration
        """
        if self.shape_preview_window is not None:
            # Recreate the preview with new config
            self.show_shape_preview(shape_config)
        else:
            # If no preview exists, just show it
            self.show_shape_preview(shape_config)

    def _scan_all_ports_simultaneously(self, input_ports: List[str], scan_time: int = 10) -> Tuple[Optional[str], Optional[Any]]:
        """
        Open ALL input ports at once and listen simultaneously.

        This is MUCH more user-friendly than sequential scanning because:
        - User can press button anytime in the 10-second window
        - Not dependent on timing the press to a specific port's 2-second window

        Args:
            input_ports: List of MIDI input port names to scan
            scan_time: Seconds to listen (default 10)

        Returns:
            (port_name, first_message) or (None, None) if no MIDI found
        """
        import mido
        import threading

        found_port = [None]
        found_msg = [None]
        stop_flag = threading.Event()

        def listen_on_port(port_name: str):
            """Thread function to listen on one port."""
            try:
                with mido.open_input(port_name) as port:
                    while not stop_flag.is_set():
                        msg = port.receive(block=False)
                        if msg and msg.type in ['note_on', 'note_off', 'control_change']:
                            # Skip note_on with velocity 0 (it's actually note_off)
                            if msg.type == 'note_on' and msg.velocity == 0:
                                continue
                            # Found MIDI!
                            if found_port[0] is None:  # First one wins
                                found_port[0] = port_name
                                found_msg[0] = msg
                            stop_flag.set()  # Stop all threads
                            return
                        time.sleep(0.02)  # 20ms polling
            except Exception:
                pass  # Port couldn't be opened, skip it

        # Start thread for each port
        threads = []
        for port_name in input_ports:
            t = threading.Thread(target=listen_on_port, args=(port_name,), daemon=True)
            t.start()
            threads.append(t)

        # Show progress
        print()
        self.print_warning("Please send MIDI now (press a button, turn a knob)")
        print()
        self.print_info(f"🔍 Scanning {len(input_ports)} ports simultaneously for {scan_time} seconds...")
        print()

        # Wait for scan_time or until MIDI found
        stop_flag.wait(timeout=scan_time)
        stop_flag.set()  # Ensure all threads stop

        # Wait for threads to finish (with timeout to avoid hanging)
        for t in threads:
            t.join(timeout=0.5)

        return found_port[0], found_msg[0]

    def _show_midi_live(self, msg: Any) -> None:
        """
        Display incoming MIDI message in real-time with color coding.

        Args:
            msg: Mido MIDI message object
        """
        if msg.type == 'note_on':
            if msg.velocity > 0:
                print(f"\r{Fore.GREEN}[MIDI] Note ON  Ch{msg.channel+1:2d} Note={msg.note:3d} Vel={msg.velocity:3d}{Style.RESET_ALL}    ", end='', flush=True)
            else:
                # Note on with velocity 0 is actually note off
                print(f"\r{Fore.CYAN}[MIDI] Note OFF Ch{msg.channel+1:2d} Note={msg.note:3d}                {Style.RESET_ALL}", end='', flush=True)
        elif msg.type == 'note_off':
            print(f"\r{Fore.CYAN}[MIDI] Note OFF Ch{msg.channel+1:2d} Note={msg.note:3d}                {Style.RESET_ALL}", end='', flush=True)
        elif msg.type == 'control_change':
            print(f"\r{Fore.YELLOW}[MIDI] CC       Ch{msg.channel+1:2d} CC={msg.control:3d} Val={msg.value:3d}     {Style.RESET_ALL}", end='', flush=True)

    def _choose_input_port_interactive(self) -> Optional[str]:
        """
        Interactive port selection with auto-scan option and retry.

        Returns:
            Selected port name, or None if cancelled
        """
        import mido

        while True:  # Retry loop for scanning
            input_ports = mido.get_input_names()

            if not input_ports:
                self.print_warning("No MIDI input ports found!")
                return None

            # Show available ports
            print(f"{Fore.CYAN}Available INPUT ports:{Style.RESET_ALL}")
            for i, port in enumerate(input_ports):
                print(f"  {i+1}. {port}")

            print()
            print(f"{Fore.CYAN}Options:{Style.RESET_ALL}")
            print(f"  {Fore.GREEN}[s]{Style.RESET_ALL} Scan all ports simultaneously (recommended)")
            print(f"  {Fore.YELLOW}[1-{len(input_ports)}]{Style.RESET_ALL} Select port manually")
            print(f"  {Fore.RED}[c]{Style.RESET_ALL} Cancel")
            print()

            choice = input(f"Your choice (s/1-{len(input_ports)}/c): ").strip().lower()

            if choice == 'c':
                return None

            if choice == 's':
                # Scan ALL ports simultaneously
                port_name, msg = self._scan_all_ports_simultaneously(input_ports, scan_time=10)

                if port_name:
                    print()
                    self.print_success(f"✓ Found active MIDI on: {port_name}")
                    if msg:
                        # Show what was detected
                        if msg.type == 'note_on':
                            print(f"  Detected: Note {msg.note} on Channel {msg.channel + 1}")
                        elif msg.type == 'control_change':
                            print(f"  Detected: CC {msg.control} on Channel {msg.channel + 1}")
                    return port_name
                else:
                    # No MIDI found - ask to retry
                    print()
                    self.print_warning("No MIDI detected on any port")
                    self.print_info("Make sure your device is sending MIDI")
                    print()
                    if self.get_yes_no("Scan again?", True):
                        print()
                        continue  # Retry scan
                    else:
                        return None  # User cancelled

            # Manual selection
            try:
                port_choice = int(choice)
                if 1 <= port_choice <= len(input_ports):
                    return input_ports[port_choice - 1]
            except ValueError:
                pass

            self.print_error("Invalid choice")
            print()
            # Loop back to show options again

    def listen_for_midi(self, timeout: int = 10, allow_port_override: bool = False) -> Optional[Dict[str, Any]]:
        """
        Listen for incoming MIDI messages with configured port support and retry.

        Args:
            timeout: Seconds to listen before timing out
            allow_port_override: If True, always prompt for port (for testing)

        Returns:
            MIDI message dict or None if cancelled
        """
        import mido

        # Check for configured input port
        configured_port = self.config['general'].get('midi_input_port', '')

        if configured_port and not allow_port_override:
            # Use configured port
            selected_port = configured_port
            self.print_info(f"Using configured MIDI input: {configured_port}")
            print()
        else:
            # Prompt for port selection
            self.print_info("MIDI Port Setup - Let's find the right port!")
            print()
            selected_port = self._choose_input_port_interactive()

            if not selected_port:
                return None  # User cancelled

        # Listen loop with retry capability
        while True:
            # Check if port is in use
            configured_output = self.config.get('general', {}).get('midi_port', '')
            if configured_output and selected_port.startswith(configured_output.rsplit(' ', 1)[0]):
                print()
                self.print_warning(f"Port '{selected_port}' might be used by running fucka")
                self.print_info("If capture fails, try: fucka stop")
                print()
                if not self.get_yes_no("Continue anyway?", False):
                    return None

            # Open the port
            try:
                midi_port = mido.open_input(selected_port)
                self.print_success(f"✓ Opened: {selected_port}")
            except Exception as e:
                self.print_error(f"Failed to open port: {e}")
                print()
                self.print_info("Try one of these:")
                print("  1. Stop fucka: fucka stop")
                print("  2. Select a different MIDI port")
                print("  3. Close other MIDI software using this port")
                return None

            # Listen for MIDI with live feedback
            captured_msg = [None]
            cancelled = [False]

            def on_press(key):
                if key == keyboard.Key.esc:
                    cancelled[0] = True
                    return False

            keyboard_listener = keyboard.Listener(on_press=on_press)
            keyboard_listener.start()

            print()
            self.print_info(f"🎵 Listening for MIDI... ({timeout}s timeout, press ESC to cancel)")
            print()

            start_time = time.time()

            try:
                while time.time() - start_time < timeout:
                    if cancelled[0]:
                        break

                    # Use receive(block=False) for reliable message capture
                    msg = midi_port.receive(block=False)

                    if msg:
                        # Show ALL incoming MIDI in real-time
                        if msg.type in ['note_on', 'note_off', 'control_change']:
                            self._show_midi_live(msg)

                        # Capture note_on with velocity > 0 or note_off
                        if msg.type == 'note_on' and msg.velocity > 0:
                            captured_msg[0] = {
                                'type': 'note',
                                'channel': msg.channel,
                                'data1': msg.note,
                                'data2': msg.velocity
                            }
                            break
                        elif msg.type == 'note_off':
                            captured_msg[0] = {
                                'type': 'note',
                                'channel': msg.channel,
                                'data1': msg.note,
                                'data2': 0
                            }
                            break
                        elif msg.type == 'control_change':
                            captured_msg[0] = {
                                'type': 'cc',
                                'channel': msg.channel,
                                'data1': msg.control,
                                'data2': msg.value
                            }
                            break

                    time.sleep(0.02)  # 20ms polling

                print()  # New line after live feedback

            finally:
                keyboard_listener.stop()
                midi_port.close()

            # Handle result
            if captured_msg[0]:
                msg = captured_msg[0]
                print()
                self.print_success(f"✓ Captured: {msg['type'].upper()} on Channel {msg['channel'] + 1}")
                print(f"  Data1 (Note/Controller): {msg['data1']}")
                print(f"  Data2 (Velocity/Value): {msg['data2']}")
                return captured_msg[0]

            elif cancelled[0]:
                print()
                self.print_info("Cancelled by user")
                return None

            else:
                # Timeout - ask to retry
                print()
                if self.get_yes_no("Timeout - no MIDI received. Listen again?", True):
                    self.print_info("Retrying...")
                    print()
                    continue  # Retry the listen loop
                else:
                    self.print_info("Cancelled")
                    return None

    def configure_general_settings(self):
        """Configure general application settings."""
        self.print_header("General Settings")

        self.config['general']['midi_port'] = self.get_input(
            "MIDI port name",
            self.config['general']['midi_port']
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
        Configure a single screen monitor (DEPRECATED - use add_screen_monitor instead).

        Returns:
            Screen monitor configuration dict
        """
        self.print_header("Configure Screen Monitor")

        monitor_id = self.get_input("Monitor ID (e.g., 'deck_a_playing')")

        # Capture pixel position (single pixel only)
        print(f"\n{Fore.CYAN}Define pixel position to monitor:{Style.RESET_ALL}")
        if self.get_yes_no("Click to capture pixel position?", True):
            position = self.capture_screen_pixel()
        else:
            position = {
                'x': int(self.get_input("X position", "100")),
                'y': int(self.get_input("Y position", "100"))
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

        if self.get_yes_no("Listen for MIDI to capture settings?", False):
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
                channel = self.get_int_input("MIDI channel (1-16)", 1, min_val=1, max_val=16)
                if midi_type == 'note':
                    note = self.get_int_input("Note number (0-127)", 60, min_val=0, max_val=127)
                    velocity_on = self.get_int_input("Velocity when matched (0-127)", 127, min_val=0, max_val=127)
                    velocity_off = self.get_int_input("Velocity when not matched (0-127)", 0, min_val=0, max_val=127)
                else:
                    controller = self.get_int_input("CC controller (0-127)", 20, min_val=0, max_val=127)
                    value_match = self.get_int_input("Value when matched (0-127)", 127, min_val=0, max_val=127)
                    value_nomatch = self.get_int_input("Value when not matched (0-127)", 0, min_val=0, max_val=127)
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
            'position': position,  # Changed from 'region' to 'position'
            'target_color': color_dict,
            'tolerance': tolerance,
            'midi_output': midi_output
        }

        self.print_success(f"Screen monitor '{monitor_id}' configured!")
        return monitor_config

    def configure_static_shape(self) -> Optional[Dict[str, Any]]:
        """
        Configure a static shape.

        Returns:
            Static shape configuration dict, or None if cancelled
        """
        self.print_header("Configure Static Shape")

        shape_id = self.get_input("Shape ID (e.g., 'deck_a_indicator')")

        # Shape type menu
        print(f"\n{Fore.CYAN}Shape type:{Style.RESET_ALL}")
        print("  1. Circle")
        print("  2. Rectangle")
        shape_choice = input("Enter choice (1-2) [1]: ").strip() or "1"

        if shape_choice == '2':
            shape_type = 'rectangle'
        else:
            shape_type = 'circle'

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

        # Show live preview of the shape
        preview_config = {
            'id': shape_id,
            'type': shape_type,
            'position': position,
            'size': size,
            'color': color
        }
        self.show_shape_preview(preview_config)

        # MIDI trigger
        print(f"\n{Fore.CYAN}Configure MIDI trigger:{Style.RESET_ALL}")
        if self.get_yes_no("Listen for MIDI to capture trigger?", True):
            midi_msg = self.listen_for_midi()

            if not midi_msg:
                # User cancelled or no MIDI found after all retries
                self.hide_shape_preview()  # Hide preview on cancellation
                print()
                self.print_warning("MIDI capture cancelled - shape not configured")
                print()
                input("Press Enter to continue...")
                return None  # DON'T configure the shape with defaults

            # Use captured MIDI values
            trigger_midi = {
                'type': midi_msg['type'],
                'channel': midi_msg['channel'],
                'note': midi_msg['data1']
            }
        else:
            # Manual input path (user chose not to listen)
            trigger_midi = {
                'type': self.get_input("Trigger type (note/cc)", "note"),
                'channel': int(self.get_input("MIDI channel (1-16)", "1")) - 1,  # Convert to 0-indexed
                'note': int(self.get_input("Note number (0-127)", "60"))
            }

        # Hide preview now that MIDI is assigned
        self.hide_shape_preview()

        # Configure MIDI behavior (what happens when MIDI signal is received)
        print(f"\n{Fore.CYAN}Configure shape behavior:{Style.RESET_ALL}")
        print("What should happen when the MIDI note is triggered?")
        print()
        print("  1. Toggle (on/off each press)")
        print("  2. Show on note_on, hide on note_off")
        print("  3. Hide on note_on, show on note_off")
        print("  4. Always visible (ignore MIDI)")
        behavior_choice = input("Enter choice (1-4) [1]: ").strip() or "1"

        if behavior_choice == '2':
            behavior = {
                'note_on': 'show',
                'note_off': 'hide'
            }
        elif behavior_choice == '3':
            behavior = {
                'note_on': 'hide',
                'note_off': 'show'
            }
        elif behavior_choice == '4':
            behavior = {
                'note_on': 'none',
                'note_off': 'none'
            }
        else:  # Default to toggle
            behavior = {
                'note_on': 'toggle',
                'note_off': 'none'
            }

        shape_config = {
            'id': shape_id,
            'type': shape_type,
            'position': position,
            'size': size,
            'color': color,
            'trigger_midi': trigger_midi,
            'behavior': behavior
        }

        self.print_success(f"Static shape '{shape_id}' configured!")
        return shape_config

    def configure_animated_shape(self) -> Optional[Dict[str, Any]]:
        """
        Configure an animated shape.

        Returns:
            Animated shape configuration dict, or None if cancelled
        """
        self.print_header("Configure Animated Shape")

        shape_id = self.get_input("Shape ID (e.g., 'crossfader_pie')")

        # Shape type menu
        print(f"\n{Fore.CYAN}Shape type:{Style.RESET_ALL}")
        print("  1. Pie Chart")
        print("  2. Progress Bar")
        shape_choice = input("Enter choice (1-2) [1]: ").strip() or "1"

        if shape_choice == '2':
            shape_type = 'progress_bar'
        else:
            shape_type = 'pie_chart'

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

        # Show live preview of the shape
        preview_config = {
            'id': shape_id,
            'type': shape_type,
            'position': position,
            'size': size,
            'color': color
        }
        self.show_shape_preview(preview_config)

        # MIDI control
        print(f"\n{Fore.CYAN}Configure MIDI CC control:{Style.RESET_ALL}")
        if self.get_yes_no("Listen for MIDI CC to capture controller?", True):
            self.print_info("Move a fader or knob on your controller to send CC")
            midi_msg = self.listen_for_midi()

            if not midi_msg:
                # User cancelled or no MIDI found after all retries
                self.hide_shape_preview()  # Hide preview on cancellation
                print()
                self.print_warning("MIDI capture cancelled - shape not configured")
                print()
                input("Press Enter to continue...")
                return None  # DON'T configure the shape with defaults

            # Use captured MIDI values
            control_midi = {
                'type': 'cc',
                'channel': midi_msg['channel'],
                'controller': midi_msg['data1']
            }
        else:
            # Manual input path (user chose not to listen)
            control_midi = {
                'type': 'cc',
                'channel': int(self.get_input("MIDI channel (1-16)", "1")) - 1,  # Convert to 0-indexed
                'controller': int(self.get_input("CC controller (0-127)", "10"))
            }

        # Hide preview now that MIDI is assigned
        self.hide_shape_preview()

        # Configure shape behavior (how CC values affect the animation)
        print(f"\n{Fore.CYAN}Configure animation behavior:{Style.RESET_ALL}")
        print("Define how the MIDI CC value (0-127) controls the shape animation.")
        print()

        if shape_type == 'pie_chart':
            start_angle = int(self.get_input("Start angle (degrees, 0=top)", "0"))
            print()
            print("Fill direction:")
            print("  1. Clockwise")
            print("  2. Counterclockwise")
            fill_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
            fill_direction = 'counterclockwise' if fill_choice == '2' else 'clockwise'

            animation = {
                'start_angle': start_angle,
                'end_angle_range': [0, 360],
                'fill_direction': fill_direction,
                'cc_mapping': 'linear'  # CC 0-127 maps to 0-360 degrees
            }
        else:  # progress_bar
            print("Bar orientation:")
            print("  1. Horizontal")
            print("  2. Vertical")
            direction_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
            direction = 'vertical' if direction_choice == '2' else 'horizontal'

            print()
            print("Fill direction:")
            if direction == 'horizontal':
                print("  1. Left to right")
                print("  2. Right to left")
                fill_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
                fill_direction = 'right_to_left' if fill_choice == '2' else 'left_to_right'
            else:
                print("  1. Bottom to top")
                print("  2. Top to bottom")
                fill_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
                fill_direction = 'top_to_bottom' if fill_choice == '2' else 'bottom_to_top'

            animation = {
                'direction': direction,
                'fill_direction': fill_direction,
                'cc_mapping': 'linear'  # CC 0-127 maps to 0-100%
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
                # Mark as saved only if validation passed
                self.mark_saved()
            except ConfigValidationError as e:
                self.print_error(f"Configuration validation failed: {e}")
                self.print_warning("Configuration saved but validation failed - review and fix errors")

        except Exception as e:
            self.print_error(f"Failed to save configuration: {e}")

    def run(self):
        """Run the interactive configuration menu."""
        try:
            while True:
                action = self.show_main_menu()
                if action == 'exit':
                    break

        except KeyboardInterrupt:
            print("\n")
            if self.confirm_exit():
                print()
                self.print_info("Configuration menu closed")
                return
        except Exception as e:
            print("\n\n")
            self.print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()

    def show_main_menu(self) -> str:
        """
        Display main menu and handle user selection.

        Returns:
            'continue' to stay in menu, 'exit' to quit
        """
        self.print_menu_header("Rekordbox MIDI Helper Config", show_breadcrumb=False)

        # Count items from active preset
        preset = self.get_active_preset()
        monitor_count = len(preset.get('screen_monitors', []))
        static_count = len(preset.get('shapes', {}).get('static', []))
        animated_count = len(preset.get('shapes', {}).get('animated', []))

        # Display menu options
        print(f"{Fore.CYAN}[1]{Style.RESET_ALL} General Settings")
        print(f"{Fore.CYAN}[2]{Style.RESET_ALL} Screen Monitors ({monitor_count} items)")
        print(f"{Fore.CYAN}[3]{Style.RESET_ALL} Static Shapes ({static_count} items)")
        print(f"{Fore.CYAN}[4]{Style.RESET_ALL} Animated Shapes ({animated_count} items)")
        print(f"{Fore.CYAN}[5]{Style.RESET_ALL} Test & Validate")
        print(f"{Fore.CYAN}[6]{Style.RESET_ALL} Save Configuration")
        print(f"{Fore.CYAN}[7]{Style.RESET_ALL} Load Configuration")
        print(f"{Fore.CYAN}[8]{Style.RESET_ALL} Manage Presets")
        print(f"{Fore.GREEN}[s]{Style.RESET_ALL} Save")
        print(f"{Fore.RED}[q]{Style.RESET_ALL} Exit")

        # Show status bar
        self.print_status_bar()

        # Get choice
        print()
        choice = input(f"Enter choice (1-8, q, s to save): ").strip().lower()

        # Handle choice
        if choice == 's':
            self.save_config()
        elif choice == '1':
            self.menu_general_settings()
        elif choice == '2':
            self.menu_screen_monitors()
        elif choice == '3':
            self.menu_static_shapes()
        elif choice == '4':
            self.menu_animated_shapes()
        elif choice == '5':
            self.menu_test_validate()
        elif choice == '6':
            self.menu_save_config()
        elif choice == '7':
            self.menu_load_config()
        elif choice == '8':
            self.menu_manage_presets()
        elif choice == 'q':
            if self.confirm_exit():
                return 'exit'
        else:
            self.print_warning("Invalid choice, please try again")

        return 'continue'

    def confirm_exit(self) -> bool:
        """
        Confirm exit if there are unsaved changes.

        Returns:
            True if user confirms exit, False otherwise
        """
        if self.unsaved_changes:
            print()
            self.print_warning("You have unsaved changes!")
            return self.get_yes_no("Are you sure you want to exit?", False)
        return True

    def configure_midi_port(self):
        """Configure MIDI port for loopMIDI (Windows)."""
        import mido

        print(f"\n{Fore.CYAN}MIDI Port Configuration (Windows loopMIDI){Style.RESET_ALL}\n")
        print("loopMIDI creates virtual MIDI ports that applications can use to communicate.")
        print()

        # List available output ports (loopMIDI ports show up here)
        try:
            available = mido.get_output_names()
        except Exception as e:
            self.print_error(f"Failed to list MIDI ports: {e}")
            return

        if not available:
            self.print_error("No MIDI ports found!")
            print("\n" + "="*60)
            print("You need to install loopMIDI:")
            print("="*60)
            print("1. Download: https://www.tobias-erichsen.de/software/loopmidi.html")
            print("2. Install and launch loopMIDI application")
            print("3. Enter a port name (e.g., 'loopMIDI Port')")
            print("4. Click the '+' button to create the port")
            print("5. Run this configuration again")
            print("="*60 + "\n")
            return

        print(f"{Fore.CYAN}Available MIDI Ports:{Style.RESET_ALL}\n")
        current_port = self.config.get('general', {}).get('midi_port', 'loopMIDI Port')

        for i, port in enumerate(available):
            current_marker = ""
            if port == current_port:
                current_marker = f" {Fore.GREEN}<-- current{Style.RESET_ALL}"
            print(f"  {i+1}. {port}{current_marker}")

        print()
        choice = self.get_int_input(
            f"Select MIDI port (1-{len(available)})",
            1,
            min_val=1,
            max_val=len(available)
        )

        selected_port = available[choice - 1]

        # Save to config
        self.config['general']['midi_port'] = selected_port

        print()
        self.print_success(f"MIDI port configured: {selected_port}")
        print()
        print(f"{Fore.CYAN}Next steps:{Style.RESET_ALL}")
        print("  1. Make sure loopMIDI is running with this port")
        print("  2. Configure Bome MIDI Translator Pro to use the same port")
        print("  3. Save this configuration (press 's')")
        print()

    def configure_midi_input_port(self):
        """Configure the global MIDI input port for listening to Bome/hardware."""
        self.print_header("Configure MIDI Input Port")

        print()
        self.print_info("This is the port where fucka LISTENS for MIDI")
        self.print_info("(e.g., 'Bome MIDI Translator 1' where Bome sends MIDI)")
        print()

        # Show current setting
        current = self.config['general'].get('midi_input_port', '')
        if current:
            self.print_success(f"Current: {current}")
        else:
            self.print_warning("Not configured - will prompt on each use")

        print()
        if not self.get_yes_no("Configure MIDI input port now?", True):
            return

        # Interactive port selection
        port_name = self._choose_input_port_interactive()

        if port_name:
            self.config['general']['midi_input_port'] = port_name
            self.print_success(f"✓ Set MIDI input port to: {port_name}")
        else:
            self.print_info("Configuration cancelled")

        print()
        input("Press Enter to continue...")

    def menu_general_settings(self):
        """General settings menu with editing."""
        self.menu_stack.append("General Settings")

        while True:
            self.print_menu_header("General Settings")

            general = self.config.get('general', {})

            # Display current settings
            print(f"{Fore.CYAN}[Current Settings]{Style.RESET_ALL}\n")
            midi_port = general.get('midi_port', 'loopMIDI Port')
            print(f"  1. MIDI Port (loopMIDI): {Fore.GREEN}{midi_port}{Style.RESET_ALL}")
            print(f"  2. Screen Monitor FPS: {Fore.GREEN}{general.get('screen_monitor_fps', 30)}{Style.RESET_ALL}")
            debug_status = "Enabled" if general.get('debug_mode', False) else "Disabled"
            debug_color = Fore.YELLOW if general.get('debug_mode', False) else Fore.GREEN
            print(f"  3. Debug Mode: {debug_color}{debug_status}{Style.RESET_ALL}")

            # Display midi_input_port
            midi_input = general.get('midi_input_port', '')
            if midi_input:
                print(f"  4. MIDI Input Port (Bome/Hardware): {Fore.GREEN}{midi_input}{Style.RESET_ALL}")
            else:
                print(f"  4. MIDI Input Port (Bome/Hardware): {Fore.YELLOW}(not configured){Style.RESET_ALL}")

            print(f"\n{Fore.CYAN}[Actions]{Style.RESET_ALL}\n")
            print(f"  {Fore.CYAN}[5]{Style.RESET_ALL} Edit setting")
            print(f"  {Fore.GREEN}[s]{Style.RESET_ALL} Save")
            print(f"  {Fore.YELLOW}[b]{Style.RESET_ALL} Back to Main Menu")
            print(f"  {Fore.RED}[q]{Style.RESET_ALL} Quit")

            self.print_status_bar()

            print()
            choice = input("Enter choice (s to save): ").strip().lower()

            # Handle global commands (q to quit, s to save)
            global_result = self.handle_global_commands(choice)
            if global_result == 'exit':
                self.menu_stack.pop()
                return
            elif global_result == 'saved':
                continue  # Redraw menu after save

            if choice == 's':
                self.save_config()
            elif choice == 'b' or choice == '0':
                break
            elif choice == 'm':
                self.menu_stack.pop()
                return
            elif choice == '5' or choice in ['1', '2', '3', '4']:
                # Allow direct selection of setting to edit
                if choice == '5':
                    print()
                    setting_choice = input("Which setting to edit? (1-4): ").strip()
                else:
                    setting_choice = choice

                if setting_choice == '1':
                    self.configure_midi_port()
                    self.mark_unsaved()
                    self.print_success("MIDI port updated")
                elif setting_choice == '2':
                    fps = self.get_int_input(
                        "Screen Monitor FPS (10-60)",
                        general.get('screen_monitor_fps', 30),
                        min_val=10,
                        max_val=60
                    )
                    self.config['general']['screen_monitor_fps'] = fps
                    self.mark_unsaved()
                    self.print_success("FPS updated")
                elif setting_choice == '3':
                    current_debug = general.get('debug_mode', False)
                    new_debug = self.get_yes_no("Enable debug mode?", current_debug)
                    if new_debug != current_debug:
                        self.config['general']['debug_mode'] = new_debug
                        self.mark_unsaved()
                        self.print_success("Debug mode updated")
                    else:
                        self.print_info("No change")
                elif setting_choice == '4':
                    self.configure_midi_input_port()
                    self.mark_unsaved()
                    self.print_success("MIDI input port updated")
                else:
                    self.print_warning("Invalid choice")

                print()
                input("Press Enter to continue...")
            else:
                self.print_warning("Invalid choice")

        self.menu_stack.pop()

    def menu_screen_monitors(self):
        """Screen monitors CRUD menu."""
        self.menu_stack.append("Screen Monitors")

        while True:
            self.print_menu_header("Screen Monitors")

            preset = self.get_active_preset()
            monitors = preset.get('screen_monitors', [])

            # List all monitors
            if monitors:
                print(f"{Fore.CYAN}[Monitors]{Style.RESET_ALL}\n")
                for i, monitor in enumerate(monitors):
                    print(f"  {i+1}. {Fore.GREEN}{monitor['id']}{Style.RESET_ALL}")

                    # Show position
                    if 'position' in monitor:
                        pos = monitor['position']
                        print(f"     Pixel: ({pos['x']}, {pos['y']})", end="")
                    elif 'region' in monitor:  # Old format
                        reg = monitor['region']
                        print(f"     Region: ({reg['x']}, {reg['y']})", end="")

                    # Show color
                    color = monitor.get('target_color', {})
                    hex_color = rgb_to_hex((color.get('r', 0), color.get('g', 0), color.get('b', 0)))
                    print(f" | Color: {hex_color}", end="")

                    # Show tolerance
                    tol = monitor.get('tolerance', 0)
                    print(f" | Tol: {tol}")

                    # Show MIDI mapping
                    midi = monitor.get('midi_output', {})
                    if midi.get('type') == 'note':
                        print(f"     MIDI: Note {midi.get('note', 0)} Ch {midi.get('channel', 1)}")
                    else:
                        print(f"     MIDI: CC {midi.get('controller', 0)} Ch {midi.get('channel', 1)}")
                    print()
            else:
                print(f"{Fore.YELLOW}No monitors configured{Style.RESET_ALL}\n")

            # Actions menu
            print(f"{Fore.CYAN}[Actions]{Style.RESET_ALL}\n")
            next_num = len(monitors) + 1
            print(f"  {Fore.CYAN}[{next_num}]{Style.RESET_ALL} Add new monitor")

            if monitors:
                print(f"  {Fore.CYAN}[{next_num + 1}]{Style.RESET_ALL} Edit monitor")
                print(f"  {Fore.CYAN}[{next_num + 2}]{Style.RESET_ALL} Delete monitor")
                print(f"  {Fore.CYAN}[{next_num + 3}]{Style.RESET_ALL} Reorder monitors")

            print(f"  {Fore.GREEN}[s]{Style.RESET_ALL} Save")
            print(f"  {Fore.YELLOW}[b]{Style.RESET_ALL} Back to Main Menu")
            print(f"  {Fore.RED}[q]{Style.RESET_ALL} Quit")

            # Show status bar
            self.print_status_bar()

            # Get choice
            print()
            choice = input(f"Enter choice (s to save): ").strip().lower()

            # Handle global commands (q to quit, s to save)
            global_result = self.handle_global_commands(choice)
            if global_result == 'exit':
                self.menu_stack.pop()
                return
            elif global_result == 'saved':
                continue  # Redraw menu after save

            # Handle choice
            if choice == 's':
                self.save_config()
            elif choice == 'b' or choice == '0':
                break
            elif choice == 'm':
                self.menu_stack.pop()
                return
            elif choice == str(next_num):
                self.add_screen_monitor()
            elif monitors:
                if choice == str(next_num + 1):
                    self.edit_screen_monitor()
                elif choice == str(next_num + 2):
                    self.delete_screen_monitor()
                elif choice == str(next_num + 3):
                    self.reorder_screen_monitors()
                else:
                    self.print_warning("Invalid choice")
            else:
                self.print_warning("Invalid choice")

        self.menu_stack.pop()

    def add_screen_monitor(self):
        """Add a new screen monitor interactively."""
        self.print_header("Add Screen Monitor")

        # Get monitor ID
        monitor_id = self.get_input("Monitor ID (e.g., 'deck_a_playing')")

        if not monitor_id:
            self.print_error("Monitor ID cannot be empty")
            return

        # Check for duplicate IDs
        preset = self.get_active_preset()
        existing_ids = [m['id'] for m in preset.get('screen_monitors', [])]
        if monitor_id in existing_ids:
            self.print_error(f"Monitor ID '{monitor_id}' already exists")
            return

        # Capture pixel position
        print(f"\n{Fore.CYAN}Define pixel position to monitor:{Style.RESET_ALL}")
        if self.get_yes_no("Click to capture pixel position?", True):
            position = self.capture_screen_pixel()

            # AUTO-CAPTURE: Get color at clicked position
            auto_color = self.capture_color_at_position(position['x'], position['y'])
            hex_auto = rgb_to_hex(auto_color)

            print(f"\n{Fore.CYAN}Color at clicked position:{Style.RESET_ALL}")
            print(f"  RGB: ({auto_color[0]}, {auto_color[1]}, {auto_color[2]})")
            print(f"  Hex: {hex_auto}")
            r, g, b = auto_color
            print(f"  Preview: \033[48;2;{r};{g};{b}m    {Style.RESET_ALL} ← Color sample")

            if self.get_yes_no("Use this color?", True):
                target_color = auto_color
                color_dict = {'r': int(target_color[0]), 'g': int(target_color[1]), 'b': int(target_color[2])}
            else:
                # Allow re-capture or manual entry
                if self.get_yes_no("Capture different color from screen?", True):
                    target_color = self.capture_color_from_screen()
                    color_dict = {'r': int(target_color[0]), 'g': int(target_color[1]), 'b': int(target_color[2])}
                else:
                    color_dict = {
                        'r': self.get_int_input("Red (0-255)", int(auto_color[0]), min_val=0, max_val=255),
                        'g': self.get_int_input("Green (0-255)", int(auto_color[1]), min_val=0, max_val=255),
                        'b': self.get_int_input("Blue (0-255)", int(auto_color[2]), min_val=0, max_val=255)
                    }
        else:
            # Manual position entry
            position = {
                'x': self.get_int_input("X position", 100, min_val=0),
                'y': self.get_int_input("Y position", 100, min_val=0)
            }

            # Still auto-capture color at manual position
            auto_color = self.capture_color_at_position(position['x'], position['y'])
            hex_auto = rgb_to_hex(auto_color)

            print(f"\n{Fore.CYAN}Color at position ({position['x']}, {position['y']}):{Style.RESET_ALL}")
            print(f"  RGB: ({auto_color[0]}, {auto_color[1]}, {auto_color[2]})")
            print(f"  Hex: {hex_auto}")
            r, g, b = auto_color
            print(f"  Preview: \033[48;2;{r};{g};{b}m    {Style.RESET_ALL} ← Color sample")

            if self.get_yes_no("Use this color?", True):
                color_dict = {'r': int(auto_color[0]), 'g': int(auto_color[1]), 'b': int(auto_color[2])}
            else:
                # Manual color entry or re-capture
                if self.get_yes_no("Capture different color from screen?", True):
                    target_color = self.capture_color_from_screen()
                    color_dict = {'r': int(target_color[0]), 'g': int(target_color[1]), 'b': int(target_color[2])}
                else:
                    color_dict = {
                        'r': self.get_int_input("Red (0-255)", int(auto_color[0]), min_val=0, max_val=255),
                        'g': self.get_int_input("Green (0-255)", int(auto_color[1]), min_val=0, max_val=255),
                        'b': self.get_int_input("Blue (0-255)", int(auto_color[2]), min_val=0, max_val=255)
                    }

        tolerance = self.get_int_input("Color tolerance (0-50, higher = less strict)", 10, min_val=0, max_val=50)

        # MIDI output configuration
        print(f"\n{Fore.CYAN}Configure MIDI output:{Style.RESET_ALL}")
        midi_type = self.get_input("MIDI type (note/cc)", "note").lower()

        if self.get_yes_no("Listen for MIDI to capture settings?", False):
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
                channel = self.get_int_input("MIDI channel (1-16)", 1, min_val=1, max_val=16)
                if midi_type == 'note':
                    note = self.get_int_input("Note number (0-127)", 60, min_val=0, max_val=127)
                    velocity_on = self.get_int_input("Velocity when matched (0-127)", 127, min_val=0, max_val=127)
                    velocity_off = self.get_int_input("Velocity when not matched (0-127)", 0, min_val=0, max_val=127)
                else:
                    controller = self.get_int_input("CC controller (0-127)", 20, min_val=0, max_val=127)
                    value_match = self.get_int_input("Value when matched (0-127)", 127, min_val=0, max_val=127)
                    value_nomatch = self.get_int_input("Value when not matched (0-127)", 0, min_val=0, max_val=127)
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

        # Create monitor config
        monitor_config = {
            'id': monitor_id,
            'position': position,
            'target_color': color_dict,
            'tolerance': tolerance,
            'midi_output': midi_output
        }

        # Add to active preset
        preset = self.get_active_preset()
        if 'screen_monitors' not in preset:
            preset['screen_monitors'] = []

        preset['screen_monitors'].append(monitor_config)
        self.mark_unsaved()

        self.print_success(f"Monitor '{monitor_id}' added successfully!")
        print()
        input("Press Enter to continue...")

    def edit_screen_monitor(self):
        """Edit an existing screen monitor."""
        preset = self.get_active_preset()
        monitors = preset.get('screen_monitors', [])

        if not monitors:
            self.print_warning("No monitors to edit")
            return

        # Show list and get selection
        print(f"\n{Fore.CYAN}Select monitor to edit:{Style.RESET_ALL}\n")
        for i, monitor in enumerate(monitors):
            print(f"  {i+1}. {monitor['id']}")

        print()
        choice = input(f"Enter number (1-{len(monitors)}), or 'b' to cancel: ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(monitors):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        monitor = monitors[index]

        # Edit submenu
        while True:
            self.print_header(f"Edit Monitor: {monitor['id']}")

            # Show current values
            print(f"{Fore.CYAN}[Current Values]{Style.RESET_ALL}\n")
            print(f"  ID: {monitor['id']}")

            if 'position' in monitor:
                pos = monitor['position']
                print(f"  Pixel: ({pos['x']}, {pos['y']})")
            elif 'region' in monitor:
                reg = monitor['region']
                print(f"  Region (old): ({reg['x']}, {reg['y']}, {reg.get('width', 0)}x{reg.get('height', 0)})")

            color = monitor.get('target_color', {})
            hex_color = rgb_to_hex((color.get('r', 0), color.get('g', 0), color.get('b', 0)))
            print(f"  Color: {hex_color} ({color.get('r', 0)}, {color.get('g', 0)}, {color.get('b', 0)})")
            print(f"  Tolerance: {monitor.get('tolerance', 0)}")

            midi = monitor.get('midi_output', {})
            if midi.get('type') == 'note':
                print(f"  MIDI: Note {midi.get('note', 0)} on Channel {midi.get('channel', 1)}")
            else:
                print(f"  MIDI: CC {midi.get('controller', 0)} on Channel {midi.get('channel', 1)}")

            # Edit options
            print(f"\n{Fore.CYAN}[Edit Options]{Style.RESET_ALL}\n")
            print("  1. Edit ID")
            print("  2. Edit pixel position")
            print("  3. Edit target color")
            print("  4. Edit tolerance")
            print("  5. Edit MIDI output")
            print("  b. Back to list")

            print()
            edit_choice = input("Enter choice: ").strip().lower()

            if edit_choice == 'b' or edit_choice == '0':
                break
            elif edit_choice == '1':
                new_id = self.get_input("New monitor ID", monitor['id'])
                if new_id and new_id != monitor['id']:
                    # Check for duplicates
                    existing_ids = [m['id'] for i, m in enumerate(monitors) if i != index]
                    if new_id in existing_ids:
                        self.print_error(f"Monitor ID '{new_id}' already exists")
                    else:
                        monitor['id'] = new_id
                        self.mark_unsaved()
                        self.print_success("ID updated")
            elif edit_choice == '2':
                print(f"\n{Fore.CYAN}Update pixel position:{Style.RESET_ALL}")
                if self.get_yes_no("Click to capture new position?", True):
                    new_pos = self.capture_screen_pixel()
                else:
                    new_pos = {
                        'x': self.get_int_input("X position", monitor.get('position', {}).get('x', 100), min_val=0),
                        'y': self.get_int_input("Y position", monitor.get('position', {}).get('y', 100), min_val=0)
                    }
                monitor['position'] = new_pos
                # Remove old region if exists
                if 'region' in monitor:
                    del monitor['region']
                self.mark_unsaved()
                self.print_success("Position updated")
            elif edit_choice == '3':
                print(f"\n{Fore.CYAN}Update target color:{Style.RESET_ALL}")
                if self.get_yes_no("Capture color from screen?", True):
                    new_color = self.capture_color_from_screen()
                    monitor['target_color'] = {'r': new_color[0], 'g': new_color[1], 'b': new_color[2]}
                else:
                    current_color = monitor.get('target_color', {})
                    monitor['target_color'] = {
                        'r': self.get_int_input("Red (0-255)", current_color.get('r', 255), min_val=0, max_val=255),
                        'g': self.get_int_input("Green (0-255)", current_color.get('g', 0), min_val=0, max_val=255),
                        'b': self.get_int_input("Blue (0-255)", current_color.get('b', 0), min_val=0, max_val=255)
                    }
                self.mark_unsaved()
                self.print_success("Color updated")
            elif edit_choice == '4':
                new_tol = self.get_int_input("Color tolerance (0-50)", monitor.get('tolerance', 10), min_val=0, max_val=50)
                monitor['tolerance'] = new_tol
                self.mark_unsaved()
                self.print_success("Tolerance updated")
            elif edit_choice == '5':
                print(f"\n{Fore.CYAN}Update MIDI output:{Style.RESET_ALL}")
                midi_type = self.get_input("MIDI type (note/cc)", monitor.get('midi_output', {}).get('type', 'note')).lower()

                if self.get_yes_no("Listen for MIDI?", False):
                    midi_msg = self.listen_for_midi()
                    if midi_msg:
                        monitor['midi_output'] = {
                            'type': midi_type,
                            'channel': midi_msg['channel']
                        }
                        if midi_type == 'note':
                            monitor['midi_output']['note'] = midi_msg['data1']
                            monitor['midi_output']['velocity_on'] = 127
                            monitor['midi_output']['velocity_off'] = 0
                        else:
                            monitor['midi_output']['controller'] = midi_msg['data1']
                            monitor['midi_output']['value_match'] = 127
                            monitor['midi_output']['value_nomatch'] = 0
                        self.mark_unsaved()
                        self.print_success("MIDI output updated")
                else:
                    current_midi = monitor.get('midi_output', {})
                    channel = self.get_int_input("MIDI channel (1-16)", current_midi.get('channel', 1), min_val=1, max_val=16)

                    if midi_type == 'note':
                        note = self.get_int_input("Note number (0-127)", current_midi.get('note', 60), min_val=0, max_val=127)
                        velocity_on = self.get_int_input("Velocity ON (0-127)", current_midi.get('velocity_on', 127), min_val=0, max_val=127)
                        velocity_off = self.get_int_input("Velocity OFF (0-127)", current_midi.get('velocity_off', 0), min_val=0, max_val=127)
                        monitor['midi_output'] = {
                            'type': 'note',
                            'channel': channel,
                            'note': note,
                            'velocity_on': velocity_on,
                            'velocity_off': velocity_off
                        }
                    else:
                        controller = self.get_int_input("CC controller (0-127)", current_midi.get('controller', 20), min_val=0, max_val=127)
                        value_match = self.get_int_input("Value when matched (0-127)", current_midi.get('value_match', 127), min_val=0, max_val=127)
                        value_nomatch = self.get_int_input("Value when not matched (0-127)", current_midi.get('value_nomatch', 0), min_val=0, max_val=127)
                        monitor['midi_output'] = {
                            'type': 'cc',
                            'channel': channel,
                            'controller': controller,
                            'value_match': value_match,
                            'value_nomatch': value_nomatch
                        }
                    self.mark_unsaved()
                    self.print_success("MIDI output updated")
            else:
                self.print_warning("Invalid choice")

    def delete_screen_monitor(self):
        """Delete a screen monitor with confirmation."""
        preset = self.get_active_preset()
        monitors = preset.get('screen_monitors', [])

        if not monitors:
            self.print_warning("No monitors to delete")
            return

        # Show list and get selection
        print(f"\n{Fore.CYAN}Select monitor to delete:{Style.RESET_ALL}\n")
        for i, monitor in enumerate(monitors):
            print(f"  {i+1}. {monitor['id']}")

        print()
        choice = input(f"Enter number (1-{len(monitors)}), or 'b' to cancel: ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(monitors):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        monitor = monitors[index]

        # Confirm deletion
        print()
        self.print_warning(f"Delete monitor '{monitor['id']}'?")
        if self.get_yes_no("This cannot be undone", False):
            monitors.pop(index)
            self.mark_unsaved()
            self.print_success(f"Monitor '{monitor['id']}' deleted")
        else:
            self.print_info("Deletion cancelled")

        print()
        input("Press Enter to continue...")

    def reorder_screen_monitors(self):
        """Reorder screen monitors interactively."""
        preset = self.get_active_preset()
        monitors = preset.get('screen_monitors', [])

        if len(monitors) < 2:
            self.print_warning("Need at least 2 monitors to reorder")
            return

        self.print_header("Reorder Screen Monitors")

        print(f"{Fore.CYAN}Current order:{Style.RESET_ALL}\n")
        for i, monitor in enumerate(monitors):
            print(f"  {i+1}. {monitor['id']}")

        print(f"\n{Fore.CYAN}Enter new order as comma-separated numbers{Style.RESET_ALL}")
        print(f"Example: 2,1,3 to swap first two monitors\n")

        order_input = input("New order: ").strip()

        if not order_input:
            self.print_info("Reorder cancelled")
            return

        try:
            # Parse input
            order = [int(x.strip()) - 1 for x in order_input.split(',')]

            # Validate
            if len(order) != len(monitors):
                self.print_error(f"Must specify {len(monitors)} numbers")
                return

            if set(order) != set(range(len(monitors))):
                self.print_error("Invalid order - must use each number exactly once")
                return

            # Reorder
            new_monitors = [monitors[i] for i in order]
            self.get_active_preset()['screen_monitors'] = new_monitors
            self.mark_unsaved()

            self.print_success("Monitors reordered!")

        except ValueError:
            self.print_error("Invalid input - use comma-separated numbers")

        print()
        input("Press Enter to continue...")

    def menu_static_shapes(self):
        """Static shapes CRUD menu."""
        self.menu_stack.append("Static Shapes")

        while True:
            self.print_menu_header("Static Shapes")

            preset = self.get_active_preset()
            shapes = preset.get('shapes', {}).get('static', [])

            # List all shapes
            if shapes:
                print(f"{Fore.CYAN}[Static Shapes]{Style.RESET_ALL}\n")
                for i, shape in enumerate(shapes):
                    print(f"  {i+1}. {Fore.GREEN}{shape['id']}{Style.RESET_ALL}")
                    print(f"     Type: {shape.get('type', 'unknown')}", end="")

                    pos = shape.get('position', {})
                    print(f" | Position: ({pos.get('x', 0)}, {pos.get('y', 0)})", end="")

                    # Show size
                    size = shape.get('size', {})
                    if 'radius' in size:
                        print(f" | Radius: {size['radius']}")
                    else:
                        print(f" | Size: {size.get('width', 0)}x{size.get('height', 0)}")

                    # Show trigger
                    trigger = shape.get('trigger_midi', {})
                    if trigger.get('type') == 'note':
                        print(f"     Trigger: Note {trigger.get('note', 0)} Ch {trigger.get('channel', 1)}")
                    else:
                        print(f"     Trigger: CC {trigger.get('controller', 0)} Ch {trigger.get('channel', 1)}")
                    print()
            else:
                print(f"{Fore.YELLOW}No static shapes configured{Style.RESET_ALL}\n")

            # Actions menu
            print(f"{Fore.CYAN}[Actions]{Style.RESET_ALL}\n")
            next_num = len(shapes) + 1
            print(f"  {Fore.CYAN}[{next_num}]{Style.RESET_ALL} Add new shape")

            if shapes:
                print(f"  {Fore.CYAN}[{next_num + 1}]{Style.RESET_ALL} Edit shape")
                print(f"  {Fore.CYAN}[{next_num + 2}]{Style.RESET_ALL} Delete shape")
                print(f"  {Fore.CYAN}[{next_num + 3}]{Style.RESET_ALL} Reorder shapes")

            print(f"  {Fore.GREEN}[s]{Style.RESET_ALL} Save")
            print(f"  {Fore.YELLOW}[b]{Style.RESET_ALL} Back to Main Menu")
            print(f"  {Fore.RED}[q]{Style.RESET_ALL} Quit")

            self.print_status_bar()

            print()
            choice = input("Enter choice (s to save): ").strip().lower()

            # Handle global commands (q to quit, s to save)
            global_result = self.handle_global_commands(choice)
            if global_result == 'exit':
                self.menu_stack.pop()
                return
            elif global_result == 'saved':
                continue  # Redraw menu after save

            if choice == 's':
                self.save_config()
            elif choice == 'b' or choice == '0':
                break
            elif choice == 'm':
                self.menu_stack.pop()
                return
            elif choice == str(next_num):
                shape_config = self.configure_static_shape()

                if shape_config is None:  # Check if configuration was cancelled
                    # Shape wasn't configured (user cancelled MIDI capture)
                    continue  # Go back to menu

                preset = self.get_active_preset()
                if 'shapes' not in preset:
                    preset['shapes'] = {}
                if 'static' not in preset['shapes']:
                    preset['shapes']['static'] = []
                preset['shapes']['static'].append(shape_config)
                self.mark_unsaved()
                self.print_success(f"Shape '{shape_config['id']}' added")
                print()
                input("Press Enter to continue...")
            elif shapes:
                if choice == str(next_num + 1):
                    self.edit_static_shape()
                elif choice == str(next_num + 2):
                    self.delete_static_shape()
                elif choice == str(next_num + 3):
                    self.reorder_static_shapes()
                else:
                    self.print_warning("Invalid choice")
            else:
                self.print_warning("Invalid choice")

        self.menu_stack.pop()

    def edit_static_shape(self):
        """Edit an existing static shape."""
        preset = self.get_active_preset()
        shapes = preset.get('shapes', {}).get('static', [])
        if not shapes:
            return

        print(f"\n{Fore.CYAN}Select shape to edit:{Style.RESET_ALL}\n")
        for i, shape in enumerate(shapes):
            print(f"  {i+1}. {shape['id']}")

        print()
        choice = input(f"Enter number (1-{len(shapes)}), or 'b' to cancel: ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(shapes):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        shape = shapes[index]

        # Simple edit: reconfigure the entire shape
        self.print_info(f"Reconfiguring shape '{shape['id']}'...")
        new_shape = self.configure_static_shape()
        shapes[index] = new_shape
        self.mark_unsaved()
        self.print_success("Shape updated")

        print()
        input("Press Enter to continue...")

    def delete_static_shape(self):
        """Delete a static shape with confirmation."""
        preset = self.get_active_preset()
        shapes = preset.get('shapes', {}).get('static', [])
        if not shapes:
            return

        print(f"\n{Fore.CYAN}Select shape to delete:{Style.RESET_ALL}\n")
        for i, shape in enumerate(shapes):
            print(f"  {i+1}. {shape['id']}")

        print()
        choice = input(f"Enter number (1-{len(shapes)}), or 'b' to cancel: ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(shapes):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        shape = shapes[index]

        print()
        self.print_warning(f"Delete shape '{shape['id']}'?")
        if self.get_yes_no("This cannot be undone", False):
            shapes.pop(index)
            self.mark_unsaved()
            self.print_success(f"Shape '{shape['id']}' deleted")
        else:
            self.print_info("Deletion cancelled")

        print()
        input("Press Enter to continue...")

    def reorder_static_shapes(self):
        """Reorder static shapes interactively."""
        preset = self.get_active_preset()
        shapes = preset.get('shapes', {}).get('static', [])
        if len(shapes) < 2:
            self.print_warning("Need at least 2 shapes to reorder")
            return

        self.print_header("Reorder Static Shapes")

        print(f"{Fore.CYAN}Current order:{Style.RESET_ALL}\n")
        for i, shape in enumerate(shapes):
            print(f"  {i+1}. {shape['id']}")

        print(f"\n{Fore.CYAN}Enter new order as comma-separated numbers{Style.RESET_ALL}")
        print(f"Example: 2,1,3 to swap first two shapes\n")

        order_input = input("New order: ").strip()

        if not order_input:
            self.print_info("Reorder cancelled")
            return

        try:
            order = [int(x.strip()) - 1 for x in order_input.split(',')]

            if len(order) != len(shapes):
                self.print_error(f"Must specify {len(shapes)} numbers")
                return

            if set(order) != set(range(len(shapes))):
                self.print_error("Invalid order - must use each number exactly once")
                return

            new_shapes = [shapes[i] for i in order]
            self.get_active_preset()['shapes']['static'] = new_shapes
            self.mark_unsaved()

            self.print_success("Shapes reordered!")

        except ValueError:
            self.print_error("Invalid input - use comma-separated numbers")

        print()
        input("Press Enter to continue...")

    def menu_animated_shapes(self):
        """Animated shapes CRUD menu."""
        self.menu_stack.append("Animated Shapes")

        while True:
            self.print_menu_header("Animated Shapes")

            preset = self.get_active_preset()
            shapes = preset.get('shapes', {}).get('animated', [])

            # List all shapes
            if shapes:
                print(f"{Fore.CYAN}[Animated Shapes]{Style.RESET_ALL}\n")
                for i, shape in enumerate(shapes):
                    print(f"  {i+1}. {Fore.GREEN}{shape['id']}{Style.RESET_ALL}")
                    print(f"     Type: {shape.get('type', 'unknown')}", end="")

                    pos = shape.get('position', {})
                    print(f" | Position: ({pos.get('x', 0)}, {pos.get('y', 0)})", end="")

                    # Show size
                    size = shape.get('size', {})
                    if 'radius' in size:
                        print(f" | Radius: {size['radius']}")
                    else:
                        print(f" | Size: {size.get('width', 0)}x{size.get('height', 0)}")

                    # Show control
                    control = shape.get('control_midi', {})
                    print(f"     Control: CC {control.get('controller', 0)} Ch {control.get('channel', 1)}")
                    print()
            else:
                print(f"{Fore.YELLOW}No animated shapes configured{Style.RESET_ALL}\n")

            # Actions menu
            print(f"{Fore.CYAN}[Actions]{Style.RESET_ALL}\n")
            next_num = len(shapes) + 1
            print(f"  {Fore.CYAN}[{next_num}]{Style.RESET_ALL} Add new shape")

            if shapes:
                print(f"  {Fore.CYAN}[{next_num + 1}]{Style.RESET_ALL} Edit shape")
                print(f"  {Fore.CYAN}[{next_num + 2}]{Style.RESET_ALL} Delete shape")
                print(f"  {Fore.CYAN}[{next_num + 3}]{Style.RESET_ALL} Reorder shapes")

            print(f"  {Fore.GREEN}[s]{Style.RESET_ALL} Save")
            print(f"  {Fore.YELLOW}[b]{Style.RESET_ALL} Back to Main Menu")
            print(f"  {Fore.RED}[q]{Style.RESET_ALL} Quit")

            self.print_status_bar()

            print()
            choice = input("Enter choice (s to save): ").strip().lower()

            # Handle global commands (q to quit, s to save)
            global_result = self.handle_global_commands(choice)
            if global_result == 'exit':
                self.menu_stack.pop()
                return
            elif global_result == 'saved':
                continue  # Redraw menu after save

            if choice == 's':
                self.save_config()
            elif choice == 'b' or choice == '0':
                break
            elif choice == 'm':
                self.menu_stack.pop()
                return
            elif choice == str(next_num):
                shape_config = self.configure_animated_shape()

                if shape_config is None:  # Check if configuration was cancelled
                    # Shape wasn't configured (user cancelled MIDI capture)
                    continue  # Go back to menu

                preset = self.get_active_preset()
                if 'shapes' not in preset:
                    preset['shapes'] = {}
                if 'animated' not in preset['shapes']:
                    preset['shapes']['animated'] = []
                preset['shapes']['animated'].append(shape_config)
                self.mark_unsaved()
                self.print_success(f"Shape '{shape_config['id']}' added")
                print()
                input("Press Enter to continue...")
            elif shapes:
                if choice == str(next_num + 1):
                    self.edit_animated_shape()
                elif choice == str(next_num + 2):
                    self.delete_animated_shape()
                elif choice == str(next_num + 3):
                    self.reorder_animated_shapes()
                else:
                    self.print_warning("Invalid choice")
            else:
                self.print_warning("Invalid choice")

        self.menu_stack.pop()

    def edit_animated_shape(self):
        """Edit an existing animated shape."""
        preset = self.get_active_preset()
        shapes = preset.get('shapes', {}).get('animated', [])
        if not shapes:
            return

        print(f"\n{Fore.CYAN}Select shape to edit:{Style.RESET_ALL}\n")
        for i, shape in enumerate(shapes):
            print(f"  {i+1}. {shape['id']}")

        print()
        choice = input(f"Enter number (1-{len(shapes)}), or 'b' to cancel: ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(shapes):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        shape = shapes[index]

        # Simple edit: reconfigure the entire shape
        self.print_info(f"Reconfiguring shape '{shape['id']}'...")
        new_shape = self.configure_animated_shape()
        shapes[index] = new_shape
        self.mark_unsaved()
        self.print_success("Shape updated")

        print()
        input("Press Enter to continue...")

    def delete_animated_shape(self):
        """Delete an animated shape with confirmation."""
        preset = self.get_active_preset()
        shapes = preset.get('shapes', {}).get('animated', [])
        if not shapes:
            return

        print(f"\n{Fore.CYAN}Select shape to delete:{Style.RESET_ALL}\n")
        for i, shape in enumerate(shapes):
            print(f"  {i+1}. {shape['id']}")

        print()
        choice = input(f"Enter number (1-{len(shapes)}), or 'b' to cancel: ").strip()

        if choice.lower() == 'b':
            return

        try:
            index = int(choice) - 1
            if index < 0 or index >= len(shapes):
                self.print_error("Invalid selection")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        shape = shapes[index]

        print()
        self.print_warning(f"Delete shape '{shape['id']}'?")
        if self.get_yes_no("This cannot be undone", False):
            shapes.pop(index)
            self.mark_unsaved()
            self.print_success(f"Shape '{shape['id']}' deleted")
        else:
            self.print_info("Deletion cancelled")

        print()
        input("Press Enter to continue...")

    def reorder_animated_shapes(self):
        """Reorder animated shapes interactively."""
        preset = self.get_active_preset()
        shapes = preset.get('shapes', {}).get('animated', [])
        if len(shapes) < 2:
            self.print_warning("Need at least 2 shapes to reorder")
            return

        self.print_header("Reorder Animated Shapes")

        print(f"{Fore.CYAN}Current order:{Style.RESET_ALL}\n")
        for i, shape in enumerate(shapes):
            print(f"  {i+1}. {shape['id']}")

        print(f"\n{Fore.CYAN}Enter new order as comma-separated numbers{Style.RESET_ALL}")
        print(f"Example: 2,1,3 to swap first two shapes\n")

        order_input = input("New order: ").strip()

        if not order_input:
            self.print_info("Reorder cancelled")
            return

        try:
            order = [int(x.strip()) - 1 for x in order_input.split(',')]

            if len(order) != len(shapes):
                self.print_error(f"Must specify {len(shapes)} numbers")
                return

            if set(order) != set(range(len(shapes))):
                self.print_error("Invalid order - must use each number exactly once")
                return

            new_shapes = [shapes[i] for i in order]
            self.get_active_preset()['shapes']['animated'] = new_shapes
            self.mark_unsaved()

            self.print_success("Shapes reordered!")

        except ValueError:
            self.print_error("Invalid input - use comma-separated numbers")

        print()
        input("Press Enter to continue...")

    def menu_test_validate(self):
        """Test and validate menu."""
        self.menu_stack.append("Test & Validate")

        while True:
            self.print_menu_header("Test & Validate")

            print(f"{Fore.CYAN}[Test Options]{Style.RESET_ALL}\n")
            print(f"  {Fore.CYAN}[1]{Style.RESET_ALL} Test MIDI connections")
            print(f"  {Fore.CYAN}[2]{Style.RESET_ALL} Validate configuration")
            print(f"  {Fore.CYAN}[3]{Style.RESET_ALL} Live preview monitors")
            print(f"  {Fore.CYAN}[4]{Style.RESET_ALL} Debug shapes (test overlay)")
            print(f"  {Fore.GREEN}[s]{Style.RESET_ALL} Save")
            print(f"  {Fore.YELLOW}[b]{Style.RESET_ALL} Back to Main Menu")
            print(f"  {Fore.RED}[q]{Style.RESET_ALL} Quit")

            self.print_status_bar()

            print()
            choice = input("Enter choice: ").strip().lower()

            # Handle global commands (q to quit, s to save)
            global_result = self.handle_global_commands(choice)
            if global_result == 'exit':
                self.menu_stack.pop()
                return
            elif global_result == 'saved':
                continue  # Redraw menu after save

            if choice == 'b' or choice == '0':
                break
            elif choice == 'm':
                self.menu_stack.pop()
                return
            elif choice == '1':
                self.test_midi_connections()
            elif choice == '2':
                self.validate_configuration()
            elif choice == '3':
                self.live_preview_monitors()
            elif choice == '4':
                self.debug_shapes()
            else:
                self.print_warning("Invalid choice")

        self.menu_stack.pop()

    def test_midi_connections(self):
        """Test MIDI input and output connections."""
        self.print_header("Test MIDI Connections")

        try:
            import mido

            # Test MIDI input
            print(f"{Fore.CYAN}MIDI Input Ports:{Style.RESET_ALL}\n")
            in_ports = mido.get_input_names()

            if in_ports:
                for i, port in enumerate(in_ports):
                    print(f"  {i+1}. {port}")
            else:
                print(f"  {Fore.YELLOW}No MIDI input ports found{Style.RESET_ALL}")

            print()

            # Test MIDI output
            print(f"{Fore.CYAN}MIDI Output Ports:{Style.RESET_ALL}\n")
            out_ports = mido.get_output_names()

            if out_ports:
                port_name = self.config.get('general', {}).get('midi_port', 'loopMIDI Port')

                for i, port in enumerate(out_ports):
                    # Highlight configured port
                    marker = f" {Fore.GREEN}(configured){Style.RESET_ALL}" if port == port_name else ""
                    print(f"  {i+1}. {port}{marker}")

                # Check if configured port exists
                if port_name in out_ports:
                    self.print_success(f"✓ Configured MIDI port '{port_name}' found!")

                    # Offer to send test message
                    if self.get_yes_no("Send test MIDI note to verify connection?", False):
                        try:
                            midi_out = mido.open_output(port_name)
                            midi_out.send(mido.Message('note_on', note=60, velocity=100, channel=0))
                            time.sleep(0.1)
                            midi_out.send(mido.Message('note_off', note=60, channel=0))
                            midi_out.close()
                            self.print_success("✓ Test MIDI message sent successfully!")
                        except Exception as e:
                            self.print_error(f"Failed to send test message: {e}")
                else:
                    self.print_warning(f"⚠ Configured port '{port_name}' not found!")
                    print(f"\n  Please install loopMIDI and create a port:")
                    print(f"  https://www.tobias-erichsen.de/software/loopmidi.html")
            else:
                print(f"  {Fore.YELLOW}No MIDI output ports found{Style.RESET_ALL}")
                print(f"\n  {Fore.YELLOW}Please install loopMIDI:{Style.RESET_ALL}")
                print(f"  1. Download: https://www.tobias-erichsen.de/software/loopmidi.html")
                print(f"  2. Install and launch loopMIDI")
                print(f"  3. Create a new port (click '+' button)")

            print()

            # Option to test listening
            if in_ports:
                if self.get_yes_no("Test MIDI input by listening for a message?", False):
                    msg = self.listen_for_midi(timeout=10)
                    if msg:
                        print()
                        self.print_success("✓ MIDI test successful!")

        except Exception as e:
            self.print_error(f"MIDI test failed: {e}")

        print()
        input("Press Enter to continue...")

    def validate_configuration(self):
        """Validate current configuration."""
        self.print_header("Validate Configuration")

        try:
            # Save to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
                temp_path = f.name

            # Try to load with ConfigLoader
            try:
                ConfigLoader(temp_path)
                self.print_success("Configuration is valid!")

                # Show summary
                print()
                print(f"{Fore.CYAN}Configuration Summary:{Style.RESET_ALL}\n")
                preset = self.get_active_preset()
                print(f"  Screen Monitors: {len(preset.get('screen_monitors', []))}")
                print(f"  Static Shapes: {len(preset.get('shapes', {}).get('static', []))}")
                print(f"  Animated Shapes: {len(preset.get('shapes', {}).get('animated', []))}")
                print(f"  MIDI Port: {self.config.get('general', {}).get('midi_port', 'N/A')}")
                print(f"  Monitor FPS: {self.config.get('general', {}).get('screen_monitor_fps', 30)}")

            except ConfigValidationError as e:
                self.print_error(f"Configuration validation failed!")
                print()
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

            finally:
                # Clean up temp file
                import os
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            self.print_error(f"Validation error: {e}")

        print()
        input("Press Enter to continue...")

    def live_preview_monitors(self):
        """Live preview of screen monitors showing current colors."""
        self.print_header("Live Preview Monitors")

        preset = self.get_active_preset()
        monitors = preset.get('screen_monitors', [])

        if not monitors:
            self.print_warning("No monitors configured")
            print()
            input("Press Enter to continue...")
            return

        self.print_info("Showing live color values for all monitors")
        self.print_info("Press Ctrl+C to stop")
        print()

        try:
            while True:
                print("\033[2J\033[H")  # Clear screen
                self.print_header("Live Monitor Preview")

                for monitor in monitors:
                    monitor_id = monitor['id']

                    # Get position
                    if 'position' in monitor:
                        pos = monitor['position']
                        x, y = pos['x'], pos['y']
                    elif 'region' in monitor:
                        reg = monitor['region']
                        x, y = reg['x'], reg['y']
                    else:
                        continue

                    # Capture current color
                    current_color = self.capture_color_at_position(x, y)
                    target_color = monitor.get('target_color', {})
                    target_rgb = (target_color.get('r', 0), target_color.get('g', 0), target_color.get('b', 0))
                    tolerance = monitor.get('tolerance', 10)

                    # Check if matches
                    from .utils.color_utils import color_matches
                    matches = color_matches(current_color, target_rgb, tolerance)

                    # Display
                    match_str = f"{Fore.GREEN}MATCH{Style.RESET_ALL}" if matches else f"{Fore.YELLOW}NO MATCH{Style.RESET_ALL}"
                    print(f"{Fore.CYAN}{monitor_id}:{Style.RESET_ALL}")
                    print(f"  Position: ({x}, {y})")
                    print(f"  Current:  RGB({current_color[0]}, {current_color[1]}, {current_color[2]})")
                    print(f"  Target:   RGB({target_rgb[0]}, {target_rgb[1]}, {target_rgb[2]})")
                    print(f"  Status:   {match_str}")
                    print()

                time.sleep(0.5)  # Update every 0.5 seconds

        except KeyboardInterrupt:
            print("\n")
            self.print_info("Preview stopped")

        print()
        input("Press Enter to continue...")

    def debug_shapes(self):
        """Debug overlay shapes - test if they appear on screen."""
        self.print_header("Debug Shapes")

        preset = self.get_active_preset()
        static_shapes = preset.get('shapes', {}).get('static', [])
        animated_shapes = preset.get('shapes', {}).get('animated', [])

        total_shapes = len(static_shapes) + len(animated_shapes)

        if total_shapes == 0:
            self.print_warning("No shapes configured")
            print()
            input("Press Enter to continue...")
            return

        # Show configured shapes
        print(f"{Fore.CYAN}Configured Shapes:{Style.RESET_ALL}\n")

        if static_shapes:
            print(f"{Fore.GREEN}Static Shapes ({len(static_shapes)}):{Style.RESET_ALL}")
            for shape in static_shapes:
                pos = shape.get('position', {})
                trigger = shape.get('trigger_midi', {})
                print(f"  • {shape['id']}: {shape['type']} at ({pos.get('x', 0)}, {pos.get('y', 0)})")
                print(f"    Trigger: {trigger.get('type', 'unknown')} CH{trigger.get('channel', 1)} "
                      f"{'Note' if trigger.get('type') == 'note' else 'CC'} {trigger.get('note', trigger.get('controller', 0))}")
            print()

        if animated_shapes:
            print(f"{Fore.GREEN}Animated Shapes ({len(animated_shapes)}):{Style.RESET_ALL}")
            for shape in animated_shapes:
                pos = shape.get('position', {})
                control = shape.get('control_midi', {})
                print(f"  • {shape['id']}: {shape['type']} at ({pos.get('x', 0)}, {pos.get('y', 0)})")
                print(f"    Control: CC{control.get('controller', 0)} CH{control.get('channel', 1)}")
            print()

        # Offer to test shape display
        print(f"{Fore.YELLOW}Shape Test Feature:{Style.RESET_ALL}\n")
        print("  This will test if the overlay window works by showing a test shape")
        print("  The test shape will appear at the top-left of your screen for 5 seconds")
        print()

        if not self.get_yes_no("Run shape test?", False):
            print()
            input("Press Enter to continue...")
            return

        # Test shape display
        self.print_info("Starting shape test...")
        self.print_info("A red circle should appear at top-left of your screen for 5 seconds")
        print()

        try:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import QTimer
            from .overlay_window import OverlayWindow
            from .utils.threading_utils import ThreadSafeQueue

            # Create Qt application
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)

            # Create overlay with a test shape
            test_shape = {
                'id': 'test_shape',
                'type': 'circle',
                'position': {'x': 100, 'y': 100},
                'size': {'radius': 50},
                'color': {'r': 255, 'g': 0, 'b': 0, 'a': 255},
                'trigger_midi': {'type': 'note', 'channel': 0, 'note': 60}
            }

            midi_queue = ThreadSafeQueue()

            overlay = OverlayWindow(
                shapes_config={'static': [test_shape], 'animated': []},
                midi_input_queue=midi_queue,
                debug=True
            )

            # Show the overlay
            overlay.show()

            self.print_success("Test shape created - it should be visible now!")
            self.print_info("Red circle at position (100, 100) with radius 50")
            self.print_info("If you don't see it, your overlay might not be working")
            print()

            # Keep it visible for 5 seconds
            for i in range(5, 0, -1):
                print(f"\rClosing in {i} seconds...", end='', flush=True)
                app.processEvents()
                time.sleep(1)

            print("\n")

            # Cleanup
            overlay.close()
            self.print_success("Test complete!")

        except Exception as e:
            self.print_error(f"Shape test failed: {e}")
            print()
            self.print_info("This could mean:")
            print("  1. PyQt5 is not installed correctly")
            print("  2. Overlay window cannot be created")
            print("  3. Your system doesn't support transparent windows")

        print()
        input("Press Enter to continue...")

    def menu_save_config(self):
        """Save configuration menu."""
        self.menu_stack.append("Save")

        try:
            self.save_config()
        except Exception as e:
            self.print_error(f"Failed to save: {e}")

        self.menu_stack.pop()

    def menu_load_config(self):
        """Load configuration menu - placeholder."""
        self.menu_stack.append("Load")
        self.print_menu_header("Load Configuration")

        if self.unsaved_changes:
            self.print_warning("You have unsaved changes!")
            if not self.get_yes_no("Load will discard unsaved changes. Continue?", False):
                self.menu_stack.pop()
                return

        print("Load configuration menu - Coming soon")
        print()
        input("Press Enter to return...")

        self.menu_stack.pop()

    def menu_manage_presets(self):
        """Manage configuration presets."""
        self.menu_stack.append("Manage Presets")

        while True:
            self.print_menu_header("Manage Presets")

            # Show current preset
            active_preset = self.get_active_preset_name()
            preset_names = self.get_preset_names()
            preset_count = len(preset_names)

            print(f"{Fore.CYAN}[Current Preset]{Style.RESET_ALL}\n")
            print(f"  Active: {Fore.GREEN}{active_preset}{Style.RESET_ALL}")
            print()

            print(f"{Fore.CYAN}[Available Presets ({preset_count})]{Style.RESET_ALL}\n")
            for i, name in enumerate(preset_names, 1):
                marker = f" {Fore.GREEN}(active){Style.RESET_ALL}" if name == active_preset else ""
                print(f"  {i}. {name}{marker}")

            print()
            print(f"{Fore.CYAN}[Actions]{Style.RESET_ALL}\n")
            print(f"  {Fore.CYAN}[s]{Style.RESET_ALL} Switch preset")
            print(f"  {Fore.CYAN}[n]{Style.RESET_ALL} Create new preset")
            print(f"  {Fore.CYAN}[c]{Style.RESET_ALL} Copy preset")
            print(f"  {Fore.CYAN}[d]{Style.RESET_ALL} Delete preset")
            print(f"  {Fore.CYAN}[r]{Style.RESET_ALL} Rename preset")
            print(f"  {Fore.GREEN}[S]{Style.RESET_ALL} Save config")
            print(f"  {Fore.YELLOW}[b]{Style.RESET_ALL} Back to Main Menu")
            print(f"  {Fore.RED}[q]{Style.RESET_ALL} Quit")

            self.print_status_bar()

            print()
            choice = input("Enter choice: ").strip().lower()

            # Handle global commands (q to quit, s to save)
            global_result = self.handle_global_commands(choice)
            if global_result == 'exit':
                self.menu_stack.pop()
                return
            elif global_result == 'saved':
                continue  # Redraw menu after save

            if choice == 'b':
                break
            elif choice == 's':
                self.switch_preset()
            elif choice == 'n':
                self.create_preset()
            elif choice == 'c':
                self.copy_preset()
            elif choice == 'd':
                self.delete_preset()
            elif choice == 'r':
                self.rename_preset()
            else:
                self.print_warning("Invalid choice")

        self.menu_stack.pop()

    def switch_preset(self):
        """Switch to a different preset."""
        print()
        print(f"{Fore.CYAN}Switch Preset{Style.RESET_ALL}\n")

        preset_names = self.get_preset_names()
        active_preset = self.get_active_preset_name()

        for i, name in enumerate(preset_names, 1):
            marker = " (current)" if name == active_preset else ""
            print(f"  {i}. {name}{marker}")

        print()
        choice = input("Enter preset number (or Enter to cancel): ").strip()

        if not choice:
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(preset_names):
                new_preset = preset_names[index]
                self.set_active_preset(new_preset)
                self.print_success(f"Switched to preset '{new_preset}'")
                print()
                input("Press Enter to continue...")
            else:
                self.print_error("Invalid preset number")
        except ValueError:
            self.print_error("Invalid input")

    def create_preset(self):
        """Create a new preset."""
        print()
        print(f"{Fore.CYAN}Create New Preset{Style.RESET_ALL}\n")

        name = input("Enter preset name: ").strip()

        if not name:
            self.print_error("Preset name cannot be empty")
            return

        if name in self.get_preset_names():
            self.print_error(f"Preset '{name}' already exists")
            return

        # Create empty preset
        self.config['presets'][name] = {
            'screen_monitors': [],
            'shapes': {
                'static': [],
                'animated': []
            }
        }
        self.mark_unsaved()

        self.print_success(f"Preset '{name}' created")

        # Ask if they want to switch to it
        if self.get_yes_no("Switch to new preset?", True):
            self.set_active_preset(name)
            self.print_success(f"Switched to preset '{name}'")

        print()
        input("Press Enter to continue...")

    def copy_preset(self):
        """Copy an existing preset."""
        print()
        print(f"{Fore.CYAN}Copy Preset{Style.RESET_ALL}\n")

        preset_names = self.get_preset_names()

        # Select source preset
        print("Select preset to copy:\n")
        for i, name in enumerate(preset_names, 1):
            print(f"  {i}. {name}")

        print()
        choice = input("Enter preset number (or Enter to cancel): ").strip()

        if not choice:
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(preset_names):
                source_name = preset_names[index]
            else:
                self.print_error("Invalid preset number")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        # Get new name
        print()
        new_name = input(f"Enter name for copy of '{source_name}': ").strip()

        if not new_name:
            self.print_error("Preset name cannot be empty")
            return

        if new_name in self.get_preset_names():
            self.print_error(f"Preset '{new_name}' already exists")
            return

        # Copy preset
        import copy
        self.config['presets'][new_name] = copy.deepcopy(self.config['presets'][source_name])
        self.mark_unsaved()

        self.print_success(f"Preset '{source_name}' copied to '{new_name}'")

        # Ask if they want to switch to it
        if self.get_yes_no("Switch to new preset?", True):
            self.set_active_preset(new_name)
            self.print_success(f"Switched to preset '{new_name}'")

        print()
        input("Press Enter to continue...")

    def delete_preset(self):
        """Delete a preset."""
        print()
        print(f"{Fore.CYAN}Delete Preset{Style.RESET_ALL}\n")

        preset_names = self.get_preset_names()

        if len(preset_names) == 1:
            self.print_error("Cannot delete the last preset")
            print()
            input("Press Enter to continue...")
            return

        active_preset = self.get_active_preset_name()

        # Select preset to delete
        print("Select preset to delete:\n")
        for i, name in enumerate(preset_names, 1):
            marker = " (current)" if name == active_preset else ""
            print(f"  {i}. {name}{marker}")

        print()
        choice = input("Enter preset number (or Enter to cancel): ").strip()

        if not choice:
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(preset_names):
                delete_name = preset_names[index]
            else:
                self.print_error("Invalid preset number")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        # Confirm deletion
        if not self.get_yes_no(f"Delete preset '{delete_name}'? This cannot be undone.", False):
            return

        # If deleting active preset, switch to another one first
        if delete_name == active_preset:
            # Find another preset to switch to
            remaining = [name for name in preset_names if name != delete_name]
            if remaining:
                self.set_active_preset(remaining[0])
                self.print_info(f"Switched to preset '{remaining[0]}'")

        # Delete preset
        del self.config['presets'][delete_name]
        self.mark_unsaved()

        self.print_success(f"Preset '{delete_name}' deleted")
        print()
        input("Press Enter to continue...")

    def rename_preset(self):
        """Rename a preset."""
        print()
        print(f"{Fore.CYAN}Rename Preset{Style.RESET_ALL}\n")

        preset_names = self.get_preset_names()
        active_preset = self.get_active_preset_name()

        # Select preset to rename
        print("Select preset to rename:\n")
        for i, name in enumerate(preset_names, 1):
            marker = " (current)" if name == active_preset else ""
            print(f"  {i}. {name}{marker}")

        print()
        choice = input("Enter preset number (or Enter to cancel): ").strip()

        if not choice:
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(preset_names):
                old_name = preset_names[index]
            else:
                self.print_error("Invalid preset number")
                return
        except ValueError:
            self.print_error("Invalid input")
            return

        # Get new name
        print()
        new_name = input(f"Enter new name for '{old_name}': ").strip()

        if not new_name:
            self.print_error("Preset name cannot be empty")
            return

        if new_name in self.get_preset_names():
            self.print_error(f"Preset '{new_name}' already exists")
            return

        # Rename preset
        self.config['presets'][new_name] = self.config['presets'][old_name]
        del self.config['presets'][old_name]

        # Update active preset if needed
        if old_name == active_preset:
            self.config['general']['active_preset'] = new_name

        self.mark_unsaved()

        self.print_success(f"Preset renamed from '{old_name}' to '{new_name}'")
        print()
        input("Press Enter to continue...")


def main():
    """Main entry point for configuration wizard."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive configuration wizard for Rekordbox MIDI Helper"
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to save configuration file (default: ~/.config/fucka/config.yaml)'
    )
    parser.add_argument(
        '--edit',
        type=str,
        help='Edit existing configuration file'
    )

    args = parser.parse_args()

    # Use specified path or default
    if args.edit:
        config_path = args.edit
    elif args.config:
        config_path = args.config
    else:
        config_path = None  # ConfigMenu will use get_config_path()

    menu = ConfigMenu(config_path)
    menu.run()


if __name__ == '__main__':
    main()
