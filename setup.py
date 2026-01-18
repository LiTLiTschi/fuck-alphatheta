"""
Setup configuration for Rekordbox MIDI Helper package.

Installs the package globally with the 'fucka' command.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="rekordbox-midi-helper",
    version="1.0.0",
    author="LiTLiTschi",
    description="Screen monitoring and MIDI overlay tool for Rekordbox DJ software",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LiTLiTschi/fuck-alphatheta",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,

    # Package data (include config templates)
    package_data={
        "": ["../config/default_config.yaml"],
    },

    # Dependencies
    install_requires=[
        "mido>=1.2.10",  # MIDI library with loopMIDI support for Windows
        "PyQt5>=5.15.0",
        "mss>=9.0.0",
        "PyYAML>=6.0",
        "numpy>=1.24.0",
        "colorama>=0.4.6",
        "pynput>=1.7.6",
        "psutil>=5.9.0",  # For process management
    ],

    # CLI entry point - creates 'fucka' command
    entry_points={
        "console_scripts": [
            "fucka=rekordbox_midi_helper.cli:main",
        ],
    },

    # Python version requirement
    python_requires=">=3.9",

    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],

    keywords="rekordbox midi dj controller bome alphatheta pioneer",

    project_urls={
        "Bug Reports": "https://github.com/LiTLiTschi/fuck-alphatheta/issues",
        "Source": "https://github.com/LiTLiTschi/fuck-alphatheta",
    },
)
