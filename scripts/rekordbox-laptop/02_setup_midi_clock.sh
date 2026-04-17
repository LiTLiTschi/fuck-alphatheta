#!/usr/bin/env bash
# Run inside WSL Debian on the rekordbox laptop.
# Installs Python + rtmidi and writes a UDP->MIDI clock converter.
# Reads JSON BPM packets from bridge.mjs on UDP 9001
# and outputs MIDI clock to a virtual MIDI port (loopMIDI / rtmidi).
set -euo pipefail

echo "=== Installing Python deps ==="
sudo apt-get install -y python3 python3-pip python3-venv libasound2-dev

MIDI_DIR="$HOME/midi-clock"
mkdir -p "$MIDI_DIR"
cd "$MIDI_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --quiet python-rtmidi

echo "=== Writing midi_clock.py ==="
cat > "$MIDI_DIR/midi_clock.py" << 'EOF'
#!/usr/bin/env python3
"""
Listens for JSON BPM packets on UDP 9001 (from bridge.mjs)
and sends MIDI clock (24 ppqn) to a virtual MIDI port.

On WSL the MIDI port is exposed to Windows via loopMIDI or
via WSL2's built-in USB/MIDI pass-through if available.
"""
import socket
import json
import time
import threading
import rtmidi

UDP_HOST = '0.0.0.0'
UDP_PORT = 9001
MIDI_PORT_NAME = 'ProLink BPM Clock'

# MIDI clock = 24 pulses per quarter note
PPQN = 24

current_bpm = None
clock_running = False

def midi_clock_thread(midi_out):
    global current_bpm, clock_running
    clock_running = True
    while clock_running:
        bpm = current_bpm
        if bpm is None or bpm <= 0:
            time.sleep(0.01)
            continue
        interval = 60.0 / (bpm * PPQN)
        midi_out.send_message([0xF8])  # MIDI clock tick
        time.sleep(interval)

def udp_listener():
    global current_bpm
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    sock.settimeout(1.0)
    print(f'Listening on UDP {UDP_HOST}:{UDP_PORT}...')
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            msg = json.loads(data.decode())
            bpm = msg.get('bpm')
            if bpm and bpm > 0:
                current_bpm = bpm
                print(f'\rBPM: {bpm:.2f}  ', end='', flush=True)
        except socket.timeout:
            continue
        except Exception as e:
            print(f'\nUDP error: {e}')

if __name__ == '__main__':
    midi_out = rtmidi.MidiOut()
    available = midi_out.get_ports()
    print('Available MIDI ports:', available)

    # Try to open existing loopMIDI port, else create virtual port
    target = next((i for i, p in enumerate(available) if 'loopMIDI' in p or 'ProLink' in p), None)
    if target is not None:
        midi_out.open_port(target)
        print(f'Opened MIDI port: {available[target]}')
    else:
        midi_out.open_virtual_port(MIDI_PORT_NAME)
        print(f'Created virtual MIDI port: {MIDI_PORT_NAME}')

    # Send MIDI Start
    midi_out.send_message([0xFA])

    t = threading.Thread(target=udp_listener, daemon=True)
    t.start()

    try:
        midi_clock_thread(midi_out)
    except KeyboardInterrupt:
        pass
    finally:
        midi_out.send_message([0xFC])  # MIDI Stop
        print('\nStopped.')
EOF

echo ""
echo "=== Done ==="
echo "Run the MIDI clock with:"
echo "  source ~/midi-clock/.venv/bin/activate"
echo "  python3 ~/midi-clock/midi_clock.py"
echo ""
echo "IMPORTANT: On WSL, virtual MIDI ports are not visible to Windows apps directly."
echo "Install loopMIDI on Windows (https://www.tobias-erichsen.de/software/loopmidi.html)"
echo "and create a port named 'loopMIDI Port' — the script will auto-connect to it."
echo "WSL -> loopMIDI -> rekordbox/lighting app on Windows."
