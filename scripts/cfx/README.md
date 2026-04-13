# Rekordbox CFX Channel Selector

A zero-latency workaround to control Rekordbox's **CFX dropdown** per channel via MIDI, using pixel-calibrated mouse clicks dispatched by AutoHotkey.

## Why this exists

Rekordbox does not expose CFX channel selection via MIDI-Out. This tool records the exact pixel positions of each dropdown option during a one-time setup, then generates a standalone `.exe` (or `.ahk` script) that maps hotkeys to those clicks.

---

## Setup (one time per machine)

```
double-click setup_cfx.bat
```

The wizard will:
1. Install Python deps (`pynput`, `pyautogui`)
2. Install AutoHotkey silently (if not present)
3. Guide you through **3 clicks per channel** to calibrate positions
4. Generate `RekordboxCFX.ahk` and compile it to **`RekordboxCFX.exe`**

---

## After Setup

**Double-click `RekordboxCFX.exe`** — that's it. No AHK needed on the target machine.

The EXE runs silently in the background and listens for hotkeys:

| Channel | Hotkey | MIDI mapping (Bome) |
|---------|--------|---------------------|
| Ch 1 | `Ctrl+Alt+1..9` | Map pad/button → keystroke |
| Ch 2 | `Ctrl+Shift+1..9` | Map pad/button → keystroke |
| Ch 3 | `Alt+Shift+1..9` | Map pad/button → keystroke |
| Ch 4 | `Ctrl+Alt+Shift+1..9` | Map pad/button → keystroke |

---

## Files

| File | Description |
|------|-------------|
| `setup_cfx.bat` | Full setup: installs deps, runs calibration, compiles EXE |
| `setup_cfx.py` | Python calibration wizard — generates `RekordboxCFX.ahk` |
| `RekordboxCFX.ahk` | Generated AHK script (created after setup) |
| `RekordboxCFX.exe` | Compiled standalone (created after setup) |
| `cfx_calibration.json` | Saved calibration data (re-run setup to recalibrate) |

---

## Notes

- Works across different resolutions and DPI scaling — calibration is per-machine
- Antivirus may flag AHK-compiled EXEs (false positive — known issue with AHK bundling)
- To recalibrate: just run `setup_cfx.bat` again
