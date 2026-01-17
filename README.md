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

1. Clone the repository:
```bash
git clone https://github.com/LiTLiTschi/fuck-alphatheta.git
cd fuck-alphatheta
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy and edit the configuration:
```bash
copy config\default_config.yaml config\config.yaml
# Edit config\config.yaml with your screen regions and MIDI mappings
```

## Quick Start

1. Start the application:
```bash
python src/main.py
```

2. The script will:
   - Create a virtual MIDI port named "Rekordbox Helper"
   - Start monitoring configured screen regions
   - Display transparent overlay with shapes
   - Send/receive MIDI messages with Bome

3. Configure Bome MIDI Translator Pro to use the "Rekordbox Helper" virtual port

## Configuration

Edit `config/config.yaml` to customize:

- Screen monitoring regions and target colors
- MIDI output mappings (notes and CC values)
- Overlay shape positions, sizes, and colors
- Animation parameters for dynamic shapes

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for detailed configuration options.

## Documentation

- [SETUP.md](docs/SETUP.md) - Detailed installation and setup guide
- [CONFIGURATION.md](docs/CONFIGURATION.md) - Complete configuration reference
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions

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
