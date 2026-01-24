"""
Configuration loader for the Rekordbox MIDI Helper.

Loads and validates YAML configuration files that define:
- General application settings
- Screen monitoring pixel positions and MIDI output mappings
- Overlay shapes (static and animated)

Supports both 'position' (new single-pixel format) and 'region' (old format)
for backward compatibility.

Example usage:
    config = ConfigLoader('config/config.yaml')
    monitors = config.get_screen_monitors()
    shapes = config.get_shapes()
"""

import yaml
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from .utils.config_path import ensure_config_exists


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """
    Loads and validates YAML configuration files.

    The configuration file should contain:
    - general: Application settings (MIDI port name, FPS, debug mode)
    - screen_monitors: List of pixel positions to monitor for color changes
    - shapes: Static and animated shapes for the overlay

    Supports both 'position' (x, y) and 'region' (x, y, width, height) formats.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Optional path to YAML configuration file. If None, uses ~/.fucka/config.yaml

        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigValidationError: If config is invalid
        """
        if config_path:
            self.config_path = config_path
        else:
            # Use default location: ~/.fucka/config.yaml
            self.config_path = str(ensure_config_exists())

        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load YAML configuration file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        if config is None:
            raise ConfigValidationError("Configuration file is empty")

        return config

    def _validate_config(self):
        """
        Validate configuration structure and required fields.

        Raises:
            ConfigValidationError: If required fields are missing or invalid
        """
        # Validate general section
        if 'general' not in self.config:
            raise ConfigValidationError("Missing 'general' section in config")

        general = self.config['general']
        if 'midi_port' not in general:
            raise ConfigValidationError("Missing 'midi_port' in general section")

        # Validate presets section
        if 'presets' not in self.config:
            raise ConfigValidationError("Missing 'presets' section in config")

        if not isinstance(self.config['presets'], dict):
            raise ConfigValidationError("'presets' must be a dictionary")

        if not self.config['presets']:
            raise ConfigValidationError("'presets' must contain at least one preset")

        # Validate each preset
        for preset_name, preset in self.config['presets'].items():
            if not isinstance(preset, dict):
                raise ConfigValidationError(f"Preset '{preset_name}' must be a dictionary")

            # Validate screen_monitors in preset (optional)
            if 'screen_monitors' in preset:
                if not isinstance(preset['screen_monitors'], list):
                    raise ConfigValidationError(f"Preset '{preset_name}': 'screen_monitors' must be a list")

                for i, monitor in enumerate(preset['screen_monitors']):
                    self._validate_screen_monitor(monitor, i)

            # Validate shapes in preset (optional)
            if 'shapes' in preset:
                if not isinstance(preset['shapes'], dict):
                    raise ConfigValidationError(f"Preset '{preset_name}': 'shapes' must be a dictionary")

                if 'static' in preset['shapes']:
                    if not isinstance(preset['shapes']['static'], list):
                        raise ConfigValidationError(f"Preset '{preset_name}': 'shapes.static' must be a list")
                    for i, shape in enumerate(preset['shapes']['static']):
                        self._validate_static_shape(shape, i)

                if 'animated' in preset['shapes']:
                    if not isinstance(preset['shapes']['animated'], list):
                        raise ConfigValidationError(f"Preset '{preset_name}': 'shapes.animated' must be a list")
                    for i, shape in enumerate(preset['shapes']['animated']):
                        self._validate_animated_shape(shape, i)

        # Validate active_preset exists
        active_preset = general.get('active_preset', 'default')
        if active_preset not in self.config['presets']:
            raise ConfigValidationError(f"Active preset '{active_preset}' does not exist in presets")

    def _validate_screen_monitor(self, monitor: Dict[str, Any], index: int):
        """Validate a single screen monitor configuration."""
        # Support both 'position' (new) and 'region' (old) formats
        required_fields = ['id', 'target_color', 'tolerance', 'midi_output']

        for field in required_fields:
            if field not in monitor:
                raise ConfigValidationError(
                    f"Screen monitor {index}: missing required field '{field}'"
                )

        # Validate position/region field
        if 'position' not in monitor and 'region' not in monitor:
            raise ConfigValidationError(
                f"Screen monitor {index}: missing 'position' or 'region' field"
            )

        # Validate position (new format) has x, y
        if 'position' in monitor:
            position = monitor['position']
            for field in ['x', 'y']:
                if field not in position:
                    raise ConfigValidationError(
                        f"Screen monitor {index}: position missing '{field}'"
                    )

        # Validate region (old format) has x, y, width, height
        if 'region' in monitor and 'position' not in monitor:
            region = monitor['region']
            for field in ['x', 'y', 'width', 'height']:
                if field not in region:
                    raise ConfigValidationError(
                        f"Screen monitor {index}: region missing '{field}'"
                    )

        # Validate target_color has r, g, b
        color = monitor['target_color']
        for field in ['r', 'g', 'b']:
            if field not in color:
                raise ConfigValidationError(
                    f"Screen monitor {index}: target_color missing '{field}'"
                )

        # Validate MIDI output
        midi_out = monitor['midi_output']
        if 'type' not in midi_out:
            raise ConfigValidationError(
                f"Screen monitor {index}: midi_output missing 'type'"
            )
        if midi_out['type'] not in ['note', 'cc']:
            raise ConfigValidationError(
                f"Screen monitor {index}: midi_output type must be 'note' or 'cc'"
            )

    def _validate_static_shape(self, shape: Dict[str, Any], index: int):
        """Validate a single static shape configuration."""
        required_fields = ['id', 'type', 'position', 'size', 'color', 'trigger_midi']

        for field in required_fields:
            if field not in shape:
                raise ConfigValidationError(
                    f"Static shape {index}: missing required field '{field}'"
                )

    def _validate_animated_shape(self, shape: Dict[str, Any], index: int):
        """Validate a single animated shape configuration."""
        required_fields = ['id', 'type', 'position', 'size', 'color', 'control_midi', 'animation']

        for field in required_fields:
            if field not in shape:
                raise ConfigValidationError(
                    f"Animated shape {index}: missing required field '{field}'"
                )

    def get_general_config(self) -> Dict[str, Any]:
        """
        Get general application configuration.

        Returns:
            Dictionary with general settings
        """
        return self.config.get('general', {})

    def get_midi_port_name(self) -> str:
        """
        Get MIDI port name for loopMIDI.

        Returns:
            MIDI port name string
        """
        return self.config['general'].get('midi_port', 'loopMIDI Port')

    def get_screen_monitor_fps(self) -> int:
        """
        Get screen monitoring FPS.

        Returns:
            FPS as integer (default: 30)
        """
        return self.config['general'].get('screen_monitor_fps', 30)

    def is_debug_mode(self) -> bool:
        """
        Check if debug mode is enabled.

        Returns:
            True if debug mode is on, False otherwise
        """
        return self.config['general'].get('debug_mode', False)

    def get_active_preset_name(self) -> str:
        """
        Get the name of the currently active preset.

        Returns:
            Active preset name
        """
        return self.config.get('general', {}).get('active_preset', 'default')

    def get_preset_names(self) -> List[str]:
        """
        Get list of all preset names.

        Returns:
            List of preset names
        """
        presets = self.config.get('presets', {})
        return list(presets.keys())

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """
        Get a specific preset by name.

        Args:
            preset_name: Name of the preset

        Returns:
            Preset configuration dictionary
        """
        presets = self.config.get('presets', {})
        return presets.get(preset_name, {'screen_monitors': [], 'shapes': {'static': [], 'animated': []}})

    def get_screen_monitors(self) -> List[Dict[str, Any]]:
        """
        Get list of screen monitor configurations from active preset.

        Returns:
            List of screen monitor dictionaries
        """
        active_preset = self.get_active_preset_name()
        preset = self.get_preset(active_preset)
        return preset.get('screen_monitors', [])

    def get_shapes(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get shape configurations from active preset.

        Returns:
            Dictionary with 'static' and 'animated' lists of shapes
        """
        active_preset = self.get_active_preset_name()
        preset = self.get_preset(active_preset)
        shapes = preset.get('shapes', {})
        return {
            'static': shapes.get('static', []),
            'animated': shapes.get('animated', [])
        }

    def get_static_shapes(self) -> List[Dict[str, Any]]:
        """Get list of static shape configurations from active preset."""
        active_preset = self.get_active_preset_name()
        preset = self.get_preset(active_preset)
        return preset.get('shapes', {}).get('static', [])

    def get_animated_shapes(self) -> List[Dict[str, Any]]:
        """Get list of animated shape configurations from active preset."""
        active_preset = self.get_active_preset_name()
        preset = self.get_preset(active_preset)
        return preset.get('shapes', {}).get('animated', [])

    def reload(self):
        """
        Reload configuration from file.

        Useful for hot-reloading configuration changes.

        Raises:
            ConfigValidationError: If reloaded config is invalid
        """
        self.config = self._load_config()
        self._validate_config()
