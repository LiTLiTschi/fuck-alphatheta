"""Configuration path utilities."""

import os
from pathlib import Path
import shutil
from typing import Optional


def get_config_dir() -> Path:
    """
    Get the configuration directory path.

    Returns:
        Path to ~/.fucka/ directory
    """
    return Path.home() / '.fucka'


def get_config_path() -> Path:
    """
    Get the configuration file path.

    Returns:
        Path to ~/.fucka/config.yaml
    """
    return get_config_dir() / 'config.yaml'


def get_default_config_template() -> Path:
    """
    Get path to default config template.

    Returns:
        Path to default_config.yaml in package
    """
    # Get path relative to this file
    utils_dir = Path(__file__).parent
    package_dir = utils_dir.parent
    project_root = package_dir.parent.parent

    return project_root / 'config' / 'default_config.yaml'


def ensure_config_dir() -> Path:
    """
    Ensure ~/.fucka/ directory exists.

    Creates directory if it doesn't exist.

    Returns:
        Path to config directory
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def ensure_config_exists() -> Path:
    """
    Ensure config file exists at ~/.fucka/config.yaml.

    If it doesn't exist, copy from default template.

    Returns:
        Path to config file
    """
    config_path = get_config_path()

    if not config_path.exists():
        # Ensure directory exists
        ensure_config_dir()

        # Copy default template
        default_template = get_default_config_template()

        if default_template.exists():
            shutil.copy(default_template, config_path)
            print(f"Created default configuration at: {config_path}")
        else:
            # Fallback: create minimal config if template not found
            minimal_config = """# Rekordbox MIDI Helper Configuration

general:
  midi_port: "loopMIDI Port"
  screen_monitor_fps: 30
  debug_mode: false

screen_monitors: []

shapes:
  static: []
  animated: []
"""
            config_path.write_text(minimal_config)
            print(f"Created minimal configuration at: {config_path}")
            print("Run 'fucka config' to set up your configuration.")

    return config_path
