import argparse
import ctypes
import json
import os
import sys
import time
from pathlib import Path

import cv2
import mss
import numpy as np
import pytesseract
import win32api

try:
    import rtmidi
except Exception:
    rtmidi = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def find_tesseract():
    env = os.environ.get("TESSERACT_CMD")
    candidates = [env] if env else []
    candidates += [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _read_key():
    """Read one keypress. Returns ('char', bytes) or ('special', bytes)."""
    try:
        import msvcrt
    except ImportError:
        return None, None
    ch = msvcrt.getch()
    if ch in (b'\x00', b'\xe0'):
        return 'special', msvcrt.getch()
    return 'char', ch


def _clear():
    os.system('cls' if os.name == 'nt' else 'clear')


set_dpi_aware()
_tess = find_tesseract()
if _tess:
    pytesseract.pytesseract.tesseract_cmd = _tess


# ---------------------------------------------------------------------------
# MIDI helpers
# ---------------------------------------------------------------------------

def _get_out_ports():
    if rtmidi is None:
        return []
    return rtmidi.MidiOut().get_ports()


def _get_in_ports():
    if rtmidi is None:
        return []
    return rtmidi.MidiIn().get_ports()


def _arrow_picker(title, subtitle, ports):
    """
    Generic arrow-key picker.
    Returns selected index, or None if cancelled (Q).
    """
    idx = 0
    while True:
        _clear()
        print("=" * 60)
        print(f"  {title}")
        print("=" * 60)
        if subtitle:
            print()
            print(f"  {subtitle}")
        print()
        for i, name in enumerate(ports):
            cursor = "  >>" if i == idx else "    "
            print(f"{cursor}  {i + 1:>2}.  {name}")
        print()
        print("  UP / DOWN  navigate    ENTER  confirm    Q  cancel")
        print()
        kind, val = _read_key()
        if kind == 'char':
            if val in (b'\r', b'\n'):
                return idx
            if val in (b'q', b'Q'):
                return None
        elif kind == 'special':
            if val == b'H':    # UP
                idx = (idx - 1) % len(ports)
            elif val == b'P':  # DOWN
                idx = (idx + 1) % len(ports)


def choose_midi_port_interactive():
    """
    Two-step arrow-key MIDI port picker.

    Step 1: pick the OUTPUT port (script sends here).
    Step 2: pick the INPUT port (DAW / MIDI monitor listens here).

    Returns (rtmidi.MidiOut, out_port_name, in_port_name) or None if cancelled.
    """
    if rtmidi is None:
        print("ERROR: python-rtmidi is not installed.")
        print("       Run: pip install python-rtmidi")
        return None

    out_ports = _get_out_ports()
    in_ports  = _get_in_ports()

    if not out_ports:
        print()
        print("  No MIDI OUTPUT ports found.")
        print("  Create a virtual loopback port first:")
        print("    Windows: install loopMIDI  https://www.tobias-erichsen.de/software/loopmidi.html")
        print("    then restart this script.")
        print()
        return None

    # --- Step 1: output port ---
    out_idx = _arrow_picker(
        "MIDI Setup  (1/2)  —  SELECT OUTPUT PORT",
        "This script SENDS MIDI on this port.",
        out_ports,
    )
    if out_idx is None:
        return None

    mo = rtmidi.MidiOut()
    mo.open_port(out_idx)
    out_name = out_ports[out_idx]

    # --- Step 2: input port ---
    if not in_ports:
        _clear()
        print()
        print(f"  Output port opened : {out_name}")
        print()
        print("  WARNING: No MIDI INPUT ports found.")
        print("  Your DAW / MIDI monitor cannot receive until an input port exists.")
        print("  (loopMIDI creates a matching input port automatically.)")
        print()
        return mo, out_name, None

    in_idx = _arrow_picker(
        "MIDI Setup  (2/2)  —  SELECT INPUT PORT",
        "Open THIS port as INPUT in your DAW / MIDI monitor.",
        in_ports,
    )
    if in_idx is None:
        return None

    in_name = in_ports[in_idx]

    _clear()
    print()
    print(f"  Output port (script sends)  : {out_name}")
    print(f"  Input port  (DAW listens)   : {in_name}")
    print()
    print(f"  >>> Open '{in_name}' as INPUT in your DAW / MIDI monitor now.")
    print()
    return mo, out_name, in_name


class MidiOutput:
    """Wraps an already-opened rtmidi.MidiOut or opens one by port substring."""

    def __init__(self, midi_out=None, port_name=None, in_port_name=None,
                 port_substr=None, channel=1):
        self.channel      = max(1, min(16, int(channel))) - 1
        self.midi         = None
        self.opened_name  = port_name or ""
        self.in_port_name = in_port_name or ""

        if midi_out is not None:
            self.midi = midi_out
            return

        if port_substr and rtmidi is not None:
            mo     = rtmidi.MidiOut()
            ports  = mo.get_ports()
            needle = port_substr.lower()
            for i, name in enumerate(ports):
                if needle in name.lower():
                    mo.open_port(i)
                    self.midi        = mo
                    self.opened_name = name
                    # best-guess input port if none was explicitly chosen
                    if not self.in_port_name:
                        in_ports = _get_in_ports()
                        match = next((p for p in in_ports if needle in p.lower()), None)
                        self.in_port_name = match or ""
                    return

    def available(self):
        return self.midi is not None

    def send_cc(self, cc, value):
        if not self.available():
            return
        status = 0xB0 | self.channel
        self.midi.send_message([status, int(cc) & 0x7F, max(0, min(127, int(value)))])

    def test(self, cc_left=20, cc_right=21):
        """Send a quick test pulse so the user can verify the connection."""
        if not self.available():
            print("  MIDI not available, skipping test.")
            return
        print()
        print("  ---- MIDI Test ----")
        print(f"  Sending on OUTPUT port : {self.opened_name}")
        if self.in_port_name:
            print(f"  >>> Your DAW / monitor INPUT port : {self.in_port_name}")
        else:
            print("  >>> Open the matching INPUT port in your DAW / MIDI monitor.")
        print(f"  Sending: CC{cc_left}=1, CC{cc_right}=2  then  CC{cc_left}=0, CC{cc_right}=0")
        print("  Watch your MIDI monitor for incoming CC messages...")
        print()
        self.send_cc(cc_left, 1)
        time.sleep(0.2)
        self.send_cc(cc_right, 2)
        time.sleep(0.2)
        self.send_cc(cc_left, 0)
        self.send_cc(cc_right, 0)
        print("  Test sent. Did your MIDI monitor show the messages? (y/n)")
        kind, val = _read_key()
        if kind == 'char' and val in (b'y', b'Y'):
            print("  Great — MIDI is working!")
        else:
            print()
            print("  MIDI not received. Common causes:")
            print("    1. DAW/monitor is open on the OUTPUT port, not the INPUT port.")
            if self.in_port_name:
                print(f"       Make sure it is listening on INPUT port: '{self.in_port_name}'")
            print("    2. loopMIDI is not running (check the system tray).")
            print(f"    3. Wrong MIDI channel: script sends on ch {self.channel + 1}.")
            print(f"       Set your DAW to receive on channel {self.channel + 1} or 'All'.")
            print()


# ---------------------------------------------------------------------------
# OCR / screen capture
# ---------------------------------------------------------------------------

class DeckDetector:
    def __init__(self, config_path):
        self.config_path = Path(config_path)
        self.sct = mss.mss()
        self.config = self.load_config() if self.config_path.exists() else None

    def load_config(self):
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, config):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def grab(self, region):
        x, y, w, h = [int(v) for v in region]
        mon = {"left": x, "top": y, "width": w, "height": h}
        return np.array(self.sct.grab(mon))

    def preprocess(self, img, threshold=170, invert=False, scale=10):
        if img.shape[2] == 4:
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        if invert:
            gray = 255 - gray
        _, bw = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        bw = cv2.copyMakeBorder(bw, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=0)
        return bw

    def ocr_digit(self, bw):
        configs = [
            "--oem 3 --psm 10 -c tessedit_char_whitelist=1234 -c classify_bln_numeric_mode=1",
            "--oem 3 --psm 13 -c tessedit_char_whitelist=1234 -c classify_bln_numeric_mode=1",
        ]
        for cfg in configs:
            txt = pytesseract.image_to_string(bw, config=cfg)
            digits = [ch for ch in txt if ch in "1234"]
            if digits:
                return digits[0]
        return "?"

    def detect_side(self, side_name):
        side = self.config["sides"][side_name]
        img  = self.grab(side["region"])
        bw   = self.preprocess(
            img,
            threshold=side.get("threshold", 170),
            invert=side.get("invert", False),
            scale=side.get("scale", 10),
        )
        digit = self.ocr_digit(bw)
        if digit == "?":
            bw_alt = self.preprocess(
                img,
                threshold=side.get("threshold", 170),
                invert=not side.get("invert", False),
                scale=max(side.get("scale", 10), 12),
            )
            alt = self.ocr_digit(bw_alt)
            if alt != "?":
                return alt, bw_alt
        return digit, bw

    def detect(self):
        left,  _ = self.detect_side("left")
        right, _ = self.detect_side("right")
        return {"left": left, "right": right, "ts": time.time()}

    def write_state(self, state, write_txt=None, write_json=None):
        if write_txt:
            Path(write_txt).parent.mkdir(parents=True, exist_ok=True)
            Path(write_txt).write_text(
                f"L={state['left']} R={state['right']}\n",
                encoding="utf-8",
            )
        if write_json:
            Path(write_json).parent.mkdir(parents=True, exist_ok=True)
            Path(write_json).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def run_live(self, write_txt=None, write_json=None, interval_ms=80, debug=False,
                 midi=None, cc_left=20, cc_right=21):
        if not self.config:
            raise RuntimeError("No config found. Run with --setup first.")
        if midi and midi.available():
            print(f"  MIDI output : {midi.opened_name}  ch={midi.channel + 1}  CC-left={cc_left}  CC-right={cc_right}")
            if midi.in_port_name:
                print(f"  DAW input   : {midi.in_port_name}")
        else:
            print("  MIDI disabled.")
        print("  Running. Ctrl+C to stop.")
        pending      = None
        pending_hits = 0
        last_written = None
        while True:
            state = self.detect()
            pair  = (state["left"], state["right"])
            if pair == pending:
                pending_hits += 1
            else:
                pending      = pair
                pending_hits = 1
            if pending_hits >= 2 and pair != last_written:
                self.write_state(state, write_txt=write_txt, write_json=write_json)
                if midi:
                    midi.send_cc(cc_left,  0 if state["left"]  == "?" else int(state["left"]))
                    midi.send_cc(cc_right, 0 if state["right"] == "?" else int(state["right"]))
                last_written = pair
                if debug:
                    print(f"  L={state['left']} R={state['right']}")
            time.sleep(interval_ms / 1000.0)

    def wait_key(self, key):
        vk = ord(key.upper()) if isinstance(key, str) else key
        while True:
            if win32api.GetAsyncKeyState(vk) & 0x8000:
                while win32api.GetAsyncKeyState(vk) & 0x8000:
                    time.sleep(0.02)
                return win32api.GetCursorPos()
            time.sleep(0.01)

    def pick_region(self, label):
        print()
        print(f"  [{label}] Move mouse to TOP-LEFT of the deck number, then press S.")
        p1 = self.wait_key("S")
        print(f"  [{label}] Move mouse to BOTTOM-RIGHT of the deck number, then press E.")
        p2 = self.wait_key("E")
        x1, y1 = p1
        x2, y2 = p2
        x, y = min(x1, x2), min(y1, y2)
        w, h = abs(x2 - x1), abs(y2 - y1)
        if w < 3 or h < 3:
            raise RuntimeError(f"Region for {label} too small: {(x, y, w, h)}")
        print(f"  [{label}] Captured: x={x} y={y} w={w} h={h}")
        return [x, y, w, h]

    def tune_region(self, label, region):
        threshold = 170
        invert    = False
        scale     = 10
        window    = f"Deck OCR Setup - {label}"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        print()
        print(f"  [{label}] Preview window open (click it to focus).")
        print("    [ / ]   threshold down / up")
        print("    I       toggle invert")
        print("    9 / 0   scale down / up")
        print("    ENTER   accept      ESC  cancel")
        while True:
            img    = self.grab(region)
            bw     = self.preprocess(img, threshold=threshold, invert=invert, scale=scale)
            digit  = self.ocr_digit(bw)
            preview = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            cv2.putText(preview, f"{label}: {digit}", (12, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(preview, f"thr={threshold} inv={invert} scale={scale}",
                        (12, preview.shape[0] - 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2, cv2.LINE_AA)
            cv2.imshow(window, preview)
            key = cv2.waitKey(25) & 0xFF
            if   key in (13, 10):                             break
            elif key == 27:       cv2.destroyWindow(window);  raise KeyboardInterrupt()
            elif key in (ord(']'), ord('='), ord('+')): threshold = min(250, threshold + 1)
            elif key in (ord('['), ord('-'), ord('_')): threshold = max(1,   threshold - 1)
            elif key in (ord('i'), ord('I')):           invert = not invert
            elif key == ord('0'): scale = min(20, scale + 1)
            elif key == ord('9'): scale = max(4,  scale - 1)
        cv2.destroyWindow(window)
        return {"region": region, "threshold": threshold, "invert": invert, "scale": scale}

    def run_setup(self, midi=None, cc_left=20, cc_right=21):
        _clear()
        print("=" * 60)
        print("  Rekordbox Deck Output  —  Setup Wizard")
        print("=" * 60)
        print()
        if midi and midi.available():
            print(f"  MIDI output port : {midi.opened_name}  (ch {midi.channel + 1})")
            if midi.in_port_name:
                print(f"  DAW input port   : {midi.in_port_name}")
                print(f"  >>> Open '{midi.in_port_name}' as INPUT in your DAW / MIDI monitor.")
            else:
                print("  >>> Open the matching INPUT port in your DAW / MIDI monitor.")
            print()
        else:
            print("  MIDI: disabled  (use --choose-midi or --midi-port to enable)")
            print()
        print("  Make sure Rekordbox is visible and showing deck numbers 1/2/3/4.")
        print("  Press any key to continue...")
        _read_key()

        left_region  = self.pick_region("LEFT")
        left_cfg     = self.tune_region("LEFT",  left_region)
        right_region = self.pick_region("RIGHT")
        right_cfg    = self.tune_region("RIGHT", right_region)

        config = {"version": 1, "sides": {"left": left_cfg, "right": right_cfg}}
        self.save_config(config)
        self.config = config
        print()
        print(f"  Config saved: {self.config_path}")

        if midi and midi.available():
            midi.test(cc_left=cc_left, cc_right=cc_right)

        print()
        print("  Live readout (Ctrl+C to stop):")
        while True:
            state = self.detect()
            print(f"\r  LEFT={state['left']}  RIGHT={state['right']}   ", end="", flush=True)
            time.sleep(0.12)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Rekordbox deck-number OCR → MIDI CC output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--setup",    action="store_true", help="Run interactive calibration wizard")
    parser.add_argument("--config",   default="deck_output_config.json", help="Calibration config file")
    parser.add_argument("--interval", type=int, default=80, help="Screen-poll interval in ms")
    parser.add_argument("--debug",    action="store_true", help="Print every deck-change to stdout")

    gf = parser.add_argument_group("file output")
    gf.add_argument("--write-txt",  default="deck_state.txt", help="Text file updated on deck change")
    gf.add_argument("--write-json", default="",               help="JSON file updated on deck change")

    gm = parser.add_argument_group(
        "MIDI output",
        "Sends CC on deck change (value = deck 1-4, 0 = unknown).\n"
        "Requires: pip install python-rtmidi\n"
        "Script sends on OUTPUT port; DAW listens on INPUT port.",
    )
    gm.add_argument("--list-midi",    action="store_true", help="List all MIDI ports then exit")
    gm.add_argument("--choose-midi",  action="store_true", help="Two-step interactive port picker")
    gm.add_argument("--midi-port",    default="",          help="Substring of MIDI output port name")
    gm.add_argument("--midi-in-port", default="",          help="Substring of MIDI input port name (for display/test only)")
    gm.add_argument("--midi-channel", type=int, default=1, help="MIDI channel 1-16")
    gm.add_argument("--midi-cc-left",  type=int, default=20, help="CC number for LEFT deck")
    gm.add_argument("--midi-cc-right", type=int, default=21, help="CC number for RIGHT deck")

    args = parser.parse_args()

    if args.list_midi:
        if rtmidi is None:
            print("ERROR: python-rtmidi not installed  (pip install python-rtmidi)")
            sys.exit(1)
        out_ports = _get_out_ports()
        in_ports  = _get_in_ports()
        print()
        print("  OUTPUT ports (script sends here):")
        for i, n in enumerate(out_ports): print(f"    {i:>2}: {n}")
        if not out_ports: print("    (none)")
        print()
        print("  INPUT ports (DAW / MIDI monitor listens here):")
        for i, n in enumerate(in_ports):  print(f"    {i:>2}: {n}")
        if not in_ports: print("    (none)")
        print()
        sys.exit(0)

    if not find_tesseract():
        print("ERROR: Tesseract OCR not found.")
        print("  Download : https://github.com/UB-Mannheim/tesseract/wiki")
        print("  Or set TESSERACT_CMD environment variable.")
        sys.exit(1)

    midi = None
    if args.choose_midi:
        result = choose_midi_port_interactive()
        if result:
            mo, out_name, in_name = result
            midi = MidiOutput(midi_out=mo, port_name=out_name,
                              in_port_name=in_name, channel=args.midi_channel)
        else:
            print("  MIDI selection cancelled. Running without MIDI.")
    elif args.midi_port:
        if rtmidi is None:
            print("WARN: python-rtmidi not installed  (pip install python-rtmidi)")
        else:
            # resolve explicit in-port name if given
            in_name = ""
            if args.midi_in_port:
                in_ports = _get_in_ports()
                needle   = args.midi_in_port.lower()
                in_name  = next((p for p in in_ports if needle in p.lower()), "")
            midi = MidiOutput(port_substr=args.midi_port,
                              in_port_name=in_name,
                              channel=args.midi_channel)
            if midi.available():
                print(f"  MIDI output port : {midi.opened_name}")
                if midi.in_port_name:
                    print(f"  DAW input port   : {midi.in_port_name}")
            else:
                print(f"  WARN: No MIDI output port matching '{args.midi_port}'.")
                print("        Use --list-midi or --choose-midi.")

    detector = DeckDetector(args.config)

    if args.setup:
        try:
            detector.run_setup(midi=midi,
                               cc_left=args.midi_cc_left,
                               cc_right=args.midi_cc_right)
        except KeyboardInterrupt:
            print("\n  Setup cancelled.")
    else:
        try:
            detector.run_live(
                write_txt=args.write_txt or None,
                write_json=args.write_json or None,
                interval_ms=args.interval,
                debug=args.debug,
                midi=midi,
                cc_left=args.midi_cc_left,
                cc_right=args.midi_cc_right,
            )
        except KeyboardInterrupt:
            print("\n  Stopped.")


if __name__ == "__main__":
    main()
