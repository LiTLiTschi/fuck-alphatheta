#!/usr/bin/env bash
# Run inside WSL Debian on the rekordbox laptop.
# Installs Node.js LTS + prolink-connect + rtpmidi deps.
set -euo pipefail

echo "=== Updating apt ==="
sudo apt-get update -y
sudo apt-get install -y curl git build-essential libasound2-dev

echo "=== Installing Node.js LTS via NodeSource ==="
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version
npm --version

echo "=== Installing global tools ==="
npm install -g node-gyp

echo "=== Creating prolink-bridge project ==="
BRIDGE_DIR="$HOME/prolink-bridge"
mkdir -p "$BRIDGE_DIR"
cd "$BRIDGE_DIR"

if [ ! -f package.json ]; then
  npm init -y
  # Switch to ESM
  npm pkg set type=module
fi

npm install prolink-connect

echo "=== Writing bridge.mjs ==="
cat > "$BRIDGE_DIR/bridge.mjs" << 'EOF'
import dgram from 'dgram';
import { bringOnline } from 'prolink-connect';

// UDP target — change to IP of your lighting device if on different machine
const UDP_HOST = '127.0.0.1';
const UDP_PORT = 9001;

// MIDI clock via UDP-MIDI bridge (optional, see README)
const sock = dgram.createSocket('udp4');

console.log('prolink-bridge: starting...');

async function main() {
  const network = await bringOnline();
  await network.autoconfigFromPeers();
  await network.connect();
  console.log('prolink-bridge: connected to Pro DJ Link network');

  network.statusEmitter.on('status', status => {
    if (!status.trackBPM || status.sliderPitch == null) return;
    if (status.playState !== 'playing') return;

    const bpm = parseFloat((status.trackBPM * (status.sliderPitch / 100 + 1)).toFixed(3));
    const payload = JSON.stringify({
      bpm,
      player: status.deviceId,
      master: status.isMaster ?? false,
      beat: status.beat,
      ts: Date.now()
    });

    sock.send(Buffer.from(payload), UDP_PORT, UDP_HOST, err => {
      if (err) console.error('UDP error:', err.message);
      else process.stdout.write(`\rBPM: ${bpm.toFixed(2)} player:${status.deviceId} master:${status.isMaster} `);
    });
  });
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
EOF

echo ""
echo "=== Done ==="
echo "Run the bridge with:"
echo "  node ~/prolink-bridge/bridge.mjs"
echo ""
echo "It sends JSON BPM packets to UDP 127.0.0.1:9001"
echo "Next: run 02_midi_clock.sh to convert BPM -> MIDI clock"
