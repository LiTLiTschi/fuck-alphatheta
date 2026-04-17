#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

function Write-Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

$RepoRoot   = Split-Path -Parent $MyInvocation.MyCommand.Path
$BridgeRoot = Join-Path $RepoRoot 'prolink-bridge'
$UDP_HOST   = '127.0.0.1'
$UDP_PORT   = 9001

Write-Step 'Checking winget'
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is required. Install "App Installer" from Microsoft Store first.'
}

Write-Step 'Checking Node.js'
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements --disable-interactivity
    Write-Host 'Node.js installed. You may need to open a new PowerShell window if node/npm are still not found.' -ForegroundColor Yellow
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw 'Node.js is still not available on PATH after install. Open a new terminal and run this script again.'
}

Write-Step 'Preparing prolink-bridge project'
New-Item -ItemType Directory -Force -Path $BridgeRoot | Out-Null
Push-Location $BridgeRoot

if (-not (Test-Path package.json)) {
    npm init -y | Out-Null
}

Write-Step 'Installing prolink-connect dependency'
npm install prolink-connect --save

Write-Step 'Creating bridge.mjs'
$bridgeCode = @"
import dgram from 'dgram';
import { bringOnline } from 'prolink-connect';

const UDP_HOST = '127.0.0.1';
const UDP_PORT = 9001;

async function main() {
  const sock = dgram.createSocket('udp4');
  const network = await bringOnline();

  await network.autoconfigFromPeers();
  await network.connect();

  console.log('prolink-bridge: connected to Pro DJ Link network');

  network.statusEmitter.on('status', status => {
    if (!status.trackBPM || status.sliderPitch == null) return;

    const bpm = status.trackBPM * (status.sliderPitch / 100 + 1);
    const payload = JSON.stringify({
      bpm,
      player: status.deviceId,
      playing: status.playState === 'playing',
      time: status.trackElapsed
    });

    const buf = Buffer.from(payload);
    sock.send(buf, UDP_PORT, UDP_HOST, err => {
      if (err) console.error('UDP send error:', err);
      else console.log('BPM sent:', bpm.toFixed(2), '| player:', status.deviceId);
    });
  });
}

main().catch(err => {
  console.error('prolink-bridge fatal error:', err);
  process.exit(1);
});
"@

Set-Content -Path (Join-Path $BridgeRoot 'bridge.mjs') -Value $bridgeCode -Encoding UTF8

Write-Step 'Done'
Write-Host "Bridge project created at: $BridgeRoot" -ForegroundColor Green
Write-Host 'Run it with:' -ForegroundColor Yellow
Write-Host "  cd `"$BridgeRoot`""
Write-Host '  node bridge.mjs'
Write-Host ''
Write-Host "Sends JSON BPM packets via UDP to ${UDP_HOST}:${UDP_PORT}" -ForegroundColor Yellow
Write-Host 'Receive in Python with: import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.bind(("0.0.0.0",9001))' -ForegroundColor Yellow

Pop-Location
