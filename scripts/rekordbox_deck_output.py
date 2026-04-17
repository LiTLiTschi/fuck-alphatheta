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


set_dpi_aware()
_tess = find_tesseract()
if _tess:
    pytesseract.pytesseract.tesseract_cmd = _tess


class MidiOutput:
    """Lightweight MIDI CC sender via python-rtmidi."""

    def __init__(self, port_name=None, channel=1):
        self.channel = max(1, min(16, int(channel))) - 1  # 0-indexed
        self.midi = None
        self.port_name = port_name
        self.opened_name = None
        if rtmidi is None:
            return
        self.midi = rtmidi.MidiOut()
        ports = self.midi.get_ports()
        if port_name:
            needle = port_name.lower()
            for idx, name in enumerate(ports):
                if needle in name.lower():
                    self.midi.open_port(idx)
                    self.opened_name = name
                    break
        elif ports:
            self.midi.open_port(0)
            self.opened_name = ports[0]

    def available(self):
        return self.midi is not None and self.opened_name is not None

    def send_cc(self, cc, value):
        """Send a MIDI CC message. value is clamped to 0-127."""
        if not self.available():
            return
        status = 0xB0 | self.channel
        self.midi.send_message([status, int(cc) & 0x7F, max(0, min(127, int(value)))])


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
        img = self.grab(side["region"])
        bw = self.preprocess(
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
        left, _ = self.detect_side("left")
        right, _ = self.detect_side("right")
        return {
            "left": left,
            "right": right,
            "ts": time.time(),
        }

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

        pending = None
        pending_hits = 0
        last_written = None

        while True:
            state = self.detect()
            pair = (state["left"], state["right"])

            if pair == pending:
                pending_hits += 1
            else:
                pending = pair
                pending_hits = 1

            if pending_hits >= 2 and pair != last_written:
                self.write_state(state, write_txt=write_txt, write_json=write_json)
                if midi:
                    midi.send_cc(cc_left, 0 if state["left"] == "?" else int(state["left"]))
                    midi.send_cc(cc_right, 0 if state["right"] == "?" else int(state["right"]))
                last_written = pair
                if debug:
                    print(f"L={state['left']} R={state['right']}")

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
        print(f"[{label}] Maus auf OBEN-LINKS der kleinen Deck-Zahl setzen und S druecken.")
        p1 = self.wait_key("S")
        print(f"[{label}] Maus auf UNTEN-RECHTS der kleinen Deck-Zahl setzen und E druecken.")
        p2 = self.wait_key("E")

        x1, y1 = p1
        x2, y2 = p2
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        if w < 3 or h < 3:
            raise RuntimeError(f"Region for {label} is too small: {(x, y, w, h)}")

        return [x, y, w, h]

    def tune_region(self, label, region):
        threshold = 170
        invert = False
        scale = 10

        window = f"Deck OCR Setup - {label}"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)

        print()
        print(f"[{label}] Preview-Fenster aktiv.")
        print("Tasten im Preview-Fenster:")
        print("  [ / ]  = Threshold runter/rauf")
        print("  I      = invert umschalten")
        print("  9 / 0  = Scale runter/rauf")
        print("  ENTER  = uebernehmen")
        print("  ESC    = abbrechen")

        while True:
            img = self.grab(region)
            bw = self.preprocess(img, threshold=threshold, invert=invert, scale=scale)
            digit = self.ocr_digit(bw)

            preview = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
            cv2.putText(
                preview,
                f"{label}: {digit}",
                (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                preview,
                f"thr={threshold} inv={invert} scale={scale}",
                (12, preview.shape[0] - 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 200, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(window, preview)
            key = cv2.waitKey(25) & 0xFF

            if key in (13, 10):
                break
            elif key == 27:
                cv2.destroyWindow(window)
                raise KeyboardInterrupt()
            elif key in (ord("]"), ord("="), ord("+")):
                threshold = min(250, threshold + 1)
            elif key in (ord("["), ord("-"), ord("_")):
                threshold = max(1, threshold - 1)
            elif key in (ord("i"), ord("I")):
                invert = not invert
            elif key == ord("0"):
                scale = min(20, scale + 1)
            elif key == ord("9"):
                scale = max(4, scale - 1)

        cv2.destroyWindow(window)
        return {
            "region": region,
            "threshold": threshold,
            "invert": invert,
            "scale": scale,
        }

    def run_setup(self):
        print("Rekordbox Deck Output Setup")
        print("===========================")
        print("Kalibriert die kleine Deck-Zahl links und rechts.")
        print("Rekordbox muss sichtbar sein und die Deck-Zahl 1/2/3/4 eingeblendet sein.")

        left_region = self.pick_region("LEFT")
        left_cfg = self.tune_region("LEFT", left_region)

        right_region = self.pick_region("RIGHT")
        right_cfg = self.tune_region("RIGHT", right_region)

        config = {
            "version": 1,
            "sides": {
                "left": left_cfg,
                "right": right_cfg,
            },
        }
        self.save_config(config)
        self.config = config

        print()
        print(f"Gespeichert: {self.config_path}")
        print("Kurzer Live-Test. STRG+C zum Beenden.")

        while True:
            state = self.detect()
            print(f"\rLEFT={state['left']} RIGHT={state['right']}   ", end="", flush=True)
            time.sleep(0.12)


def main():
    parser = argparse.ArgumentParser(
        description="Rekordbox deck-number OCR output tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # --- core ---
    parser.add_argument("--setup",      action="store_true",
                        help="Run calibration wizard")
    parser.add_argument("--config",     default="deck_output_config.json",
                        help="Path to calibration config file")
    parser.add_argument("--interval",   type=int, default=80,
                        help="Screen-poll interval in ms")
    parser.add_argument("--debug",      action="store_true",
                        help="Print every deck-change to stdout")

    # --- file output ---
    grp_file = parser.add_argument_group("file output")
    grp_file.add_argument("--write-txt",  default="deck_state.txt",
                          help="Text file written on every change (read by AHK)")
    grp_file.add_argument("--write-json", default="",
                          help="Optional JSON file written on every change")

    # --- MIDI output ---
    grp_midi = parser.add_argument_group(
        "MIDI output",
        "Sends a CC message whenever the active deck changes. "
        "Requires python-rtmidi (pip install python-rtmidi). "
        "CC value = deck number 1-4, or 0 when unknown.",
    )
    grp_midi.add_argument("--list-midi",     action="store_true",
                          help="List available MIDI output ports and exit")
    grp_midi.add_argument("--midi-port",     default="",
                          help="Substring of the MIDI output port name to open "
                               "(e.g. 'loopMIDI', 'IAC'). Leave empty to disable MIDI.")
    grp_midi.add_argument("--midi-channel",  type=int, default=1,
                          help="MIDI channel 1-16")
    grp_midi.add_argument("--midi-cc-left",  type=int, default=20,
                          help="CC number sent for the LEFT deck")
    grp_midi.add_argument("--midi-cc-right", type=int, default=21,
                          help="CC number sent for the RIGHT deck")

    args = parser.parse_args()

    # --list-midi: no Tesseract needed
    if args.list_midi:
        if rtmidi is None:
            print("ERROR: python-rtmidi is not installed  (pip install python-rtmidi)")
            sys.exit(1)
        mo = rtmidi.MidiOut()
        ports = mo.get_ports()
        if not ports:
            print("No MIDI output ports found.")
        else:
            print("Available MIDI output ports:")
            for i, name in enumerate(ports):
                print(f"  {i}: {name}")
        sys.exit(0)

    if not find_tesseract():
        print("ERROR: Tesseract not found.")
        print("Install from https://github.com/UB-Mannheim/tesseract/wiki")
        print("or set TESSERACT_CMD env var to the tesseract.exe path.")
        sys.exit(1)

    # MIDI setup
    midi = None
    if args.midi_port:
        if rtmidi is None:
            print("WARN: python-rtmidi not installed, MIDI output disabled.")
            print("      Run: pip install python-rtmidi")
        else:
            midi = MidiOutput(args.midi_port, args.midi_channel)
            if midi.available():
                print(f"MIDI output: {midi.opened_name}  ch={args.midi_channel}  "
                      f"CC-left={args.midi_cc_left}  CC-right={args.midi_cc_right}")
            else:
                print(f"WARN: MIDI port matching '{args.midi_port}' not found.")
                print("      Use --list-midi to see available ports.")

    detector = DeckDetector(args.config)

    if args.setup:
        detector.run_setup()
    else:
        detector.run_live(
            write_txt=args.write_txt or None,
            write_json=args.write_json or None,
            interval_ms=args.interval,
            debug=args.debug,
            midi=midi,
            cc_left=args.midi_cc_left,
            cc_right=args.midi_cc_right,
        )


if __name__ == "__main__":
    main()
