#!/usr/bin/env bash
# Run inside WSL Debian on the rekordbox laptop.
# Installs Python + rtmidi and writes a UDP->MIDI clock converter.
# Reads JSON BPM packets from bridge.mjs on UDP 9001
# and outputs MIDI clock to a chosen MIDI port (Bome MIDI Translator / any).
set -euo pipefail

echo "=== Installing Python deps ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv libasound2-dev

MIDI_DIR="$HOME/midi-clock"
mkdir -p "$MIDI_DIR"
cd "$MIDI_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --quiet python-rtmidi

echo "=== Writing midi_clock.py ==="
cat > "$MIDI_DIR/midi_clock.py" << 'PYEOF'
#!/usr/bin/env python3
"""
UDP -> MIDI clock bridge.
Reads JSON BPM from bridge.mjs on UDP 9001,
outputs MIDI clock (24ppqn) + Start/Stop to a user-selected MIDI port.
Also accepts an optional MIDI input port for monitoring.

Usage:
  python3 midi_clock.py              # interactive port selection
  python3 midi_clock.py --out 2      # non-interactive, output port index 2
  python3 midi_clock.py --out 2 --in 0
"""
import socket
import json
import time
import threading
import argparse
import rtmidi

UDP_HOST = '0.0.0.0'
UDP_PORT = 9001
PPQN = 24
current_bpm = None


def list_ports(midi_obj, label):
    ports = midi_obj.get_ports()
    print(f"\nAvailable {label} ports:")
    if not ports:
        print("  (none found)")
    for i, name in enumerate(ports):
        print(f"  [{i}] {name}")
    return ports


def pick_port(ports, label, forced=None):
    if not ports:
        return None
    if forced is not None:
        if 0 <= forced < len(ports):
            print(f"Using {label} port [{forced}]: {ports[forced]}")
            return forced
        print(f"Port index {forced} out of range, falling back to interactive.")
    while True:
        raw = input(f"Select {label} port index (Enter to skip): ").strip()
        if raw == '':
            return None
        if raw.isdigit() and 0 <= int(raw) < len(ports):
            return int(raw)
        print(f"  Invalid. Enter 0-{len(ports)-1}.")


def midi_clock_thread(midi_out):
    global current_bpm
    while True:
        bpm = current_bpm
        if bpm is None or bpm <= 0:
            time.sleep(0.01)
            continue
        interval = 60.0 / (bpm * PPQN)
        midi_out.send_message([0xF8])
        time.sleep(interval)


def udp_listener():
    global current_bpm
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    sock.settimeout(1.0)
    print(f'UDP listener on {UDP_HOST}:{UDP_PORT} ...')
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            msg = json.loads(data.decode())
            bpm = msg.get('bpm')
            if bpm and bpm > 0:
                current_bpm = bpm
                print(f'\r  BPM: {bpm:.3f}   ', end='', flush=True)
        except socket.timeout:
            continue
        except Exception as e:
            print(f'\nUDP error: {e}')


def main():
    parser = argparse.ArgumentParser(description='UDP BPM -> MIDI clock')
    parser.add_argument('--out', type=int, default=None, help='Output port index')
    parser.add_argument('--in', dest='inp', type=int, default=None, help='Input port index (optional)')
    args = parser.parse_args()

    # Output port
    midi_out = rtmidi.MidiOut()
    out_ports = list_ports(midi_out, 'OUTPUT')
    out_idx = pick_port(out_ports, 'OUTPUT', forced=args.out)
    if out_idx is not None:
        midi_out.open_port(out_idx)
        print(f"Opened output: {out_ports[out_idx]}")
    else:
        midi_out.open_virtual_port('ProLink BPM Clock')
        print("Created virtual output port: ProLink BPM Clock")

    # Input port (optional, for monitoring)
    midi_in = rtmidi.MidiIn()
    in_ports = list_ports(midi_in, 'INPUT')
    in_idx = pick_port(in_ports, 'INPUT (optional, monitoring only)', forced=args.inp)
    if in_idx is not None:
        midi_in.open_port(in_idx)
        print(f"Opened input: {in_ports[in_idx]}")
        midi_in.set_callback(lambda msg, _: None)
    else:
        print("No input port selected.")

    midi_out.send_message([0xFA])  # MIDI Start
    print("\nMIDI Start sent. Waiting for BPM on UDP 9001...")
    print("Ctrl+C to stop.\n")

    threading.Thread(target=udp_listener, daemon=True).start()

    try:
        midi_clock_thread(midi_out)
    except KeyboardInterrupt:
        pass
    finally:
        midi_out.send_message([0xFC])  # MIDI Stop
        print('\nMIDI Stop sent. Bye.')


if __name__ == '__main__':
    main()
PYEOF

chmod +x "$MIDI_DIR/midi_clock.py"

echo ""
echo "=== Done ==="
echo "Run:"
echo "  source ~/midi-clock/.venv/bin/activate"
echo "  python3 ~/midi-clock/midi_clock.py"
echo ""
echo "The script lists all MIDI ports (including Bome MIDI Translator virtual ports)"
echo "and lets you pick input + output interactively by index."
echo ""
echo "Non-interactive: python3 ~/midi-clock/midi_clock.py --out 2"
