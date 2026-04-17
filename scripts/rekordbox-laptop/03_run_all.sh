#!/usr/bin/env bash
# Starts both bridge.mjs and midi_clock.py in parallel.
# Run this inside WSL Debian on the rekordbox laptop.
set -euo pipefail

echo "Starting prolink-bridge..."
node ~/prolink-bridge/bridge.mjs &
BRIDGE_PID=$!
echo "  bridge PID: $BRIDGE_PID"

sleep 2

echo "Starting MIDI clock..."
source ~/midi-clock/.venv/bin/activate
python3 ~/midi-clock/midi_clock.py &
MIDI_PID=$!
echo "  midi clock PID: $MIDI_PID"

echo ""
echo "Both running. Press Ctrl+C to stop both."

trap "kill $BRIDGE_PID $MIDI_PID 2>/dev/null; echo stopped" INT TERM
wait
