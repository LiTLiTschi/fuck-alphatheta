# scripts/

All scripts for the **rekordbox BPM → MIDI clock** pipeline.

---

## Architecture

```
[rekordbox + GRV6]
  (Windows, rekordbox-laptop)
        │
        │  Pro DJ Link (LAN / loopback)
        ▼
[WSL Debian on rekordbox-laptop]
  01_setup_wsl_debian.sh    → installs Node + prolink-connect
  02_setup_midi_clock.sh    → installs Python + rtmidi
  03_run_all.sh             → starts both processes
        │
        │  bridge.mjs listens to Pro DJ Link, emits JSON BPM on UDP 9001
        │  midi_clock.py reads UDP 9001, outputs MIDI clock (24ppqn)
        │
        ▼
[loopMIDI virtual port on Windows]
        │
        ▼
[Lighting app / DAW / BLT on same or second laptop]
```

---

## Setup order (rekordbox laptop)

1. Install Debian WSL:  
   ```powershell
   wsl --install -d Debian
   ```

2. Inside WSL, clone the repo and run setup scripts:
   ```bash
   git clone https://github.com/LiTLiTschi/fuck-alphatheta ~/fuck-alphatheta
   cd ~/fuck-alphatheta/scripts/rekordbox-laptop
   bash 01_setup_wsl_debian.sh
   bash 02_setup_midi_clock.sh
   ```

3. Install **loopMIDI** on Windows (free):  
   https://www.tobias-erichsen.de/software/loopmidi.html  
   Create one port named `loopMIDI Port`.

4. Start the pipeline:
   ```bash
   bash ~/fuck-alphatheta/scripts/rekordbox-laptop/03_run_all.sh
   ```

5. In your lighting app or DAW on Windows, select **loopMIDI Port** as MIDI clock input.

---

## Files

| File | Where to run | What it does |
|---|---|---|
| `rekordbox-laptop/01_setup_wsl_debian.sh` | WSL Debian | Installs Node.js + prolink-connect + bridge.mjs |
| `rekordbox-laptop/02_setup_midi_clock.sh` | WSL Debian | Installs Python + rtmidi + midi_clock.py |
| `rekordbox-laptop/03_run_all.sh` | WSL Debian | Starts bridge + MIDI clock together |
| `setup_libcdj_windows.ps1` | Windows (dead end) | Old attempt — do not use, libcdj won't build natively |
| `setup_prolink_bridge_windows.ps1` | Windows | Old attempt — better-sqlite3 build fails on Node 20 |

---

## Notes

- WSL2 virtual MIDI ports are **not** directly visible to Windows. You must use loopMIDI as a bridge.
- `bridge.mjs` must be on the **same LAN** as rekordbox and join as a virtual Pro DJ Link device.
- rekordbox and the WSL bridge cannot both run on the same network interface at the same time without some care — if the bridge fails to connect, check that rekordbox's Pro DJ Link is enabled under Preferences → Advanced → Audio → DJ System.
