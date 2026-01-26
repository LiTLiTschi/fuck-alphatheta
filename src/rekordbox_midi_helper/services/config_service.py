"""
Configuration Service

Provides high-level interface for config operations in the TUI.
"""

import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..config_loader import ConfigLoader, ConfigValidationError


class ConfigService:
    """Service for configuration management"""

    def __init__(self, config_path: str = None):
        """
        Initialize config service.

        Args:
            config_path: Path to config file
        """
        self.config_path = config_path
        self.config_loader = ConfigLoader(config_path)
        self._unsaved_changes = False

    def mark_unsaved(self) -> None:
        """Mark configuration as having unsaved changes"""
        self._unsaved_changes = True

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes"""
        return self._unsaved_changes

    def save(self) -> None:
        """Save configuration to file"""
        with open(self.config_loader.config_path, 'w') as f:
            yaml.safe_dump(self.config_loader.config, f, default_flow_style=False, sort_keys=False)
        self._unsaved_changes = False

    def reload(self) -> None:
        """Reload configuration from file"""
        self.config_loader = ConfigLoader(self.config_path)
        self._unsaved_changes = False

    # ===== General Settings =====

    def get_general_settings(self) -> Dict[str, Any]:
        """Get all general settings"""
        return self.config_loader.get_general_config()

    def get_midi_output_port(self) -> str:
        """Get MIDI output port name"""
        return self.config_loader.get_midi_port_name()

    def set_midi_output_port(self, port_name: str) -> None:
        """Set MIDI output port name"""
        self.config_loader.config['general']['midi_port'] = port_name
        self.mark_unsaved()

    def get_midi_input_port(self) -> Optional[str]:
        """Get MIDI input port name"""
        return self.config_loader.get_midi_input_port_name()

    def set_midi_input_port(self, port_name: str) -> None:
        """Set MIDI input port name"""
        self.config_loader.config['general']['midi_input_port'] = port_name
        self.mark_unsaved()

    def get_screen_monitor_fps(self) -> int:
        """Get screen monitor FPS"""
        return self.config_loader.get_screen_monitor_fps()

    def set_screen_monitor_fps(self, fps: int) -> None:
        """Set screen monitor FPS"""
        self.config_loader.config['general']['screen_monitor_fps'] = fps
        self.mark_unsaved()

    def get_debug_mode(self) -> bool:
        """Get debug mode status"""
        return self.config_loader.is_debug_mode()

    def set_debug_mode(self, enabled: bool) -> None:
        """Set debug mode"""
        self.config_loader.config['general']['debug_mode'] = enabled
        self.mark_unsaved()

    # ===== Presets =====

    def get_active_preset_name(self) -> str:
        """Get active preset name"""
        return self.config_loader.get_active_preset_name()

    def get_preset_names(self) -> List[str]:
        """Get list of all preset names"""
        return self.config_loader.get_preset_names()

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """Get specific preset configuration"""
        return self.config_loader.get_preset(preset_name)

    def switch_preset(self, preset_name: str) -> None:
        """Switch to a different preset"""
        if preset_name not in self.get_preset_names():
            raise ValueError(f"Preset '{preset_name}' does not exist")

        self.config_loader.config['general']['active_preset'] = preset_name
        self.mark_unsaved()

    def create_preset(self, preset_name: str) -> None:
        """Create a new preset"""
        if preset_name in self.get_preset_names():
            raise ValueError(f"Preset '{preset_name}' already exists")

        self.config_loader.config['presets'][preset_name] = {
            'screen_monitors': [],
            'shapes': {
                'static': [],
                'animated': []
            }
        }
        self.mark_unsaved()

    def delete_preset(self, preset_name: str) -> None:
        """Delete a preset"""
        if preset_name not in self.get_preset_names():
            raise ValueError(f"Preset '{preset_name}' does not exist")

        if preset_name == self.get_active_preset_name():
            raise ValueError("Cannot delete active preset")

        del self.config_loader.config['presets'][preset_name]
        self.mark_unsaved()

    def copy_preset(self, source_name: str, dest_name: str) -> None:
        """Copy a preset"""
        if source_name not in self.get_preset_names():
            raise ValueError(f"Source preset '{source_name}' does not exist")

        if dest_name in self.get_preset_names():
            raise ValueError(f"Destination preset '{dest_name}' already exists")

        import copy
        self.config_loader.config['presets'][dest_name] = copy.deepcopy(
            self.config_loader.config['presets'][source_name]
        )
        self.mark_unsaved()

    # ===== Screen Monitors =====

    def get_screen_monitors(self) -> List[Dict[str, Any]]:
        """Get all screen monitors from active preset"""
        return self.config_loader.get_screen_monitors()

    def add_screen_monitor(self, monitor_data: Dict[str, Any]) -> None:
        """Add a new screen monitor"""
        active_preset = self.get_active_preset_name()
        if 'screen_monitors' not in self.config_loader.config['presets'][active_preset]:
            self.config_loader.config['presets'][active_preset]['screen_monitors'] = []

        self.config_loader.config['presets'][active_preset]['screen_monitors'].append(monitor_data)
        self.mark_unsaved()

    def update_screen_monitor(self, monitor_id: str, new_data: Dict[str, Any]) -> bool:
        """Update an existing screen monitor"""
        monitors = self.get_screen_monitors()
        for i, monitor in enumerate(monitors):
            if monitor.get('id') == monitor_id:
                active_preset = self.get_active_preset_name()
                self.config_loader.config['presets'][active_preset]['screen_monitors'][i] = new_data
                self.mark_unsaved()
                return True
        return False

    def delete_screen_monitor(self, monitor_id: str) -> bool:
        """Delete a screen monitor"""
        monitors = self.get_screen_monitors()
        active_preset = self.get_active_preset_name()

        for i, monitor in enumerate(monitors):
            if monitor.get('id') == monitor_id:
                del self.config_loader.config['presets'][active_preset]['screen_monitors'][i]
                self.mark_unsaved()
                return True
        return False

    # ===== Static Shapes =====

    def get_static_shapes(self) -> List[Dict[str, Any]]:
        """Get all static shapes from active preset"""
        return self.config_loader.get_static_shapes()

    def add_static_shape(self, shape_data: Dict[str, Any]) -> None:
        """Add a new static shape"""
        active_preset = self.get_active_preset_name()
        if 'shapes' not in self.config_loader.config['presets'][active_preset]:
            self.config_loader.config['presets'][active_preset]['shapes'] = {'static': [], 'animated': []}

        if 'static' not in self.config_loader.config['presets'][active_preset]['shapes']:
            self.config_loader.config['presets'][active_preset]['shapes']['static'] = []

        self.config_loader.config['presets'][active_preset]['shapes']['static'].append(shape_data)
        self.mark_unsaved()

    def update_static_shape(self, shape_id: str, new_data: Dict[str, Any]) -> bool:
        """Update an existing static shape"""
        shapes = self.get_static_shapes()
        for i, shape in enumerate(shapes):
            if shape.get('id') == shape_id:
                active_preset = self.get_active_preset_name()
                self.config_loader.config['presets'][active_preset]['shapes']['static'][i] = new_data
                self.mark_unsaved()
                return True
        return False

    def delete_static_shape(self, shape_id: str) -> bool:
        """Delete a static shape"""
        shapes = self.get_static_shapes()
        active_preset = self.get_active_preset_name()

        for i, shape in enumerate(shapes):
            if shape.get('id') == shape_id:
                del self.config_loader.config['presets'][active_preset]['shapes']['static'][i]
                self.mark_unsaved()
                return True
        return False

    # ===== Animated Shapes =====

    def get_animated_shapes(self) -> List[Dict[str, Any]]:
        """Get all animated shapes from active preset"""
        return self.config_loader.get_animated_shapes()

    def add_animated_shape(self, shape_data: Dict[str, Any]) -> None:
        """Add a new animated shape"""
        active_preset = self.get_active_preset_name()
        if 'shapes' not in self.config_loader.config['presets'][active_preset]:
            self.config_loader.config['presets'][active_preset]['shapes'] = {'static': [], 'animated': []}

        if 'animated' not in self.config_loader.config['presets'][active_preset]['shapes']:
            self.config_loader.config['presets'][active_preset]['shapes']['animated'] = []

        self.config_loader.config['presets'][active_preset]['shapes']['animated'].append(shape_data)
        self.mark_unsaved()

    def update_animated_shape(self, shape_id: str, new_data: Dict[str, Any]) -> bool:
        """Update an existing animated shape"""
        shapes = self.get_animated_shapes()
        for i, shape in enumerate(shapes):
            if shape.get('id') == shape_id:
                active_preset = self.get_active_preset_name()
                self.config_loader.config['presets'][active_preset]['shapes']['animated'][i] = new_data
                self.mark_unsaved()
                return True
        return False

    def delete_animated_shape(self, shape_id: str) -> bool:
        """Delete an animated shape"""
        shapes = self.get_animated_shapes()
        active_preset = self.get_active_preset_name()

        for i, shape in enumerate(shapes):
            if shape.get('id') == shape_id:
                del self.config_loader.config['presets'][active_preset]['shapes']['animated'][i]
                self.mark_unsaved()
                return True
        return False
