# Rekordbox MIDI Helper

A Python-based solution to enhance Rekordbox DJ software usability with Bome MIDI Translator Pro, designed to work around hardware limitations of the GRV6 DJ controller.

## Why This Project?

AlphaTheta (Pioneer DJ's mother company) has implemented hardware locks and jogwheel limitations that prevent proper use of Bome MIDI Translator Pro with certain controllers like the GRV6. This tool provides a workaround by:

- **Monitoring screen pixels** for color changes in Rekordbox and sending MIDI signals
- **Drawing custom overlay shapes** on top of Rekordbox based on MIDI input
- **Animating shapes dynamically** using MIDI CC values (e.g., pie charts that fill from 0-360° based on CC 0-127)

## Features

### Screen Color Detection
- Monitor specific screen regions for color changes
- Send MIDI Note On/Off and CC messages when colors match
- Configurable tolerance for color matching
- Real-time performance (30+ FPS)

### Transparent Overlay Window
- Always-on-top, click-through transparent window
- Draw custom shapes over Rekordbox interface
- Two types of shapes:
  - **Static shapes**: Triggered by MIDI notes
  - **Animated shapes**: Controlled by MIDI CC values (e.g., pie charts)

### MIDI Communication
- Creates virtual MIDI ports using python-rtmidi
- Bi-directional MIDI communication with Bome MIDI Translator Pro
- Flexible Note and CC message support

### Configuration-Driven
- All settings in YAML configuration files
- No hardcoded coordinates or MIDI mappings
- Easy to adjust without code changes

## Requirements

- **OS**: Windows 10/11
- **Python**: 3.9+
- **Bome MIDI Translator Pro** (for testing and integration)

## Installation

Install the package globally using pip:

```bash
pip install git+https://github.com/LiTLiTschi/fuck-alphatheta.git
```

Or clone and install from source:

```bash
git clone https://github.com/LiTLiTschi/fuck-alphatheta.git
cd fuck-alphatheta
pip install -e .
```

This installs the `fucka` command globally on your system.

## Quick Start

1. Run the configuration wizard:
```bash
fucka config
```

The interactive wizard provides:
- Click-based screen region selection
- Color picking from screen
- MIDI device listening and capture
- Step-by-step guided setup
- Live position tracking

2. Start the application:
```bash
fucka start
```

3. Check status:
```bash
fucka status
```

4. Configure Bome MIDI Translator Pro to use the "Rekordbox Helper" virtual port

5. Stop when done:
```bash
fucka stop
```

## Usage

The `fucka` command provides several subcommands:

```bash
fucka config              # Run interactive configuration wizard
fucka start               # Start application in background
fucka start --debug       # Start with debug logging
fucka stop                # Stop running application
fucka status              # Check if running and show stats
fucka run                 # Run in foreground (for debugging)
fucka run --debug         # Run in foreground with debug output
fucka logs                # Show recent logs
fucka logs --follow       # Follow logs in real-time
```

### Background Mode

The application runs as a background process:
- Logs are saved to `~/.fucka/fucka.log`
- PID file stored in `~/.fucka/fucka.pid`
- Survives terminal closure
- Auto-restart on crash (planned feature)

## Configuration

### Interactive Configuration Wizard

The easiest way to configure the application is using the interactive wizard:

```bash
fucka config
```

**Features:**
- **Click-based region selection**: Click two corners to define screen regions
- **Color picker**: Click anywhere on screen to capture RGB values
- **MIDI device listening**: Send MIDI from your controller to auto-capture settings
- **Live mouse position tracking**: See exact coordinates in real-time
- **Step-by-step guidance**: Wizard walks you through each setting
- **Validation**: Automatic validation before saving

**Workflow:**
1. Define general settings (MIDI port name, FPS)
2. Add screen monitors (click regions, pick colors, capture MIDI)
3. Add static shapes (click positions, listen for MIDI triggers)
4. Add animated shapes (click positions, capture MIDI CC controllers)
5. Save and validate configuration

### Manual Configuration

Edit `config/config.yaml` to customize:

- Screen monitoring regions and target colors
- MIDI output mappings (notes and CC values)
- Overlay shape positions, sizes, and colors
- Animation parameters for dynamic shapes

See `config/default_config.yaml` for a comprehensive template with detailed inline comments.

## Project Structure

```
fuck-alphatheta/
├── config/          # Configuration files
├── src/             # Source code
│   ├── shapes/      # Shape rendering classes
│   └── utils/       # Utility modules
├── tests/           # Unit tests
├── docs/            # Documentation
└── examples/        # Example configurations
```

## How It Works

1. **Screen Monitoring**: The script continuously captures specified screen regions and detects color changes
2. **MIDI Output**: When a color change is detected, MIDI messages are sent to the virtual port
3. **MIDI Input**: Incoming MIDI CC messages control shape animations in the overlay
4. **Overlay Rendering**: A transparent Qt window draws shapes on top of Rekordbox

## Performance

- Screen capture latency: <50ms
- MIDI latency: <10ms
- CPU usage: <15% during active monitoring
- Memory usage: <100MB

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgments

Created out of frustration with AlphaTheta's hardware limitations. Because DJs deserve better.
