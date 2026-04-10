import sys, os, json, time, ctypes, argparse, mss, win32api
import numpy as np
import cv2
import pytesseract
from pathlib import Path

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    ctypes.windll.user32.SetProcessDPIAware()

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class BPMEngine:
    def __init__(self, config_path=None):
        self.sct = mss.mss()
        self.config = None
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config = json.load(f)

    def get_bin(self, zone, thresh):
        mon = {"top": int(zone[1]), "left": int(zone[0]), "width": int(zone[2]), "height": int(zone[3])}
        img = np.array(self.sct.grab(mon))
        gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        _, b = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
        return b

    def recognize_current_bpm(self, config_override=None):
        cfg = config_override if config_override else self.config
        if not cfg: return "? ? . ? ?", 0
        res = []
        scores = []
        for i in range(5):
            f = self.get_bin(cfg["zones"][i], cfg["threshold"])
            best_char, max_score = "?", 0
            for digit, pix in cfg["magic_pixels"][str(i)].items():
                if not pix: continue
                score = sum(1 for p in pix if f[p[0], p[1]] == (p[2]*255)) / len(pix)
                if score > 0.85 and score > max_score:
                    max_score, best_char = score, digit
            res.append(best_char)
            scores.append(max_score)
        
        bpm_str = f"{''.join(res[:3]).strip()}.{''.join(res[3:])}"
        avg_certainty = sum(scores)/5 if scores else 0
        return bpm_str, avg_certainty, res

    def run_live(self, write_path=None, interval_ms=20, max_jump=5.0):
        print(f"[!] Engine Active. Max Jump: {max_jump} | Polling: {interval_ms}ms")
        last_valid_bpm = 0.0
        while True:
            bpm_str, cert, _ = self.recognize_current_bpm()
            if "?" not in bpm_str:
                try:
                    val = float(bpm_str)
                    if last_valid_bpm == 0 or abs(val - last_valid_bpm) <= max_jump:
                        print(f"\rBPM: {bpm_str} ({int(cert*100)}%)    ", end="")
                        if write_path: 
                            with open(write_path, "w") as f: f.write(bpm_str)
                        last_valid_bpm = val
                except: pass
            time.sleep(interval_ms / 1000.0)

class BPMWizard(BPMEngine):
    def __init__(self, interval_ms):
        super().__init__()
        self.threshold = 150
        self.interval = interval_ms
        self.patterns = {str(i): {} for i in range(5)}
        self.needed = " 0123456789"

    def cls(self): os.system('cls' if os.name == 'nt' else 'clear')

    def draw_1to1(self, frame):
        for row in frame: print("".join("██" if p > 128 else "  " for p in row))

    def run_setup(self, filename):
        while True: # Global Restart Loop
            # STAGE 1: BOUNDS
            self.cls()
            print("STAGE 1: BOUNDS\nHover Top-Left [S] | Bottom-Right [E]")
            p1 = self.wait_key(ord('S')); p2 = self.wait_key(ord('E'))
            x, y, w, h = p1[0], p1[1], p2[0]-p1[0], p2[1]-p1[1]
            cw = int(w * 0.16)
            self.zones = [[x,y,cw,h],[x+cw,y,cw,h],[x+2*cw,y,cw,h],[x+int(w*0.64),y,cw,h],[x+int(w*0.82),y,cw,h]]

            # STAGE 2: THRESHOLD
            while not (win32api.GetAsyncKeyState(0x0D) & 0x8000):
                self.cls()
                print(f"STAGE 2: THRESHOLD ({self.threshold})\n[W/S] Adjust | [ENTER] Lock")
                f = self.get_bin([x,y,w,h], self.threshold)
                self.draw_1to1(f)
                if win32api.GetAsyncKeyState(ord('W')) & 0x8000: self.threshold += 1
                if win32api.GetAsyncKeyState(ord('S')) & 0x8000: self.threshold -= 1
                time.sleep(0.05)

            # STAGE 3: FAST AUTO-SCAN
            time.sleep(0.5)
            print("\nSTAGE 3: FAST AUTO-SCAN\nMove fader slowly. [TAB] to Audit.")
            while not (win32api.GetAsyncKeyState(0x09) & 0x8000):
                f_full = self.get_bin([x,y,w,h], self.threshold)
                raw = pytesseract.image_to_string(f_full, config='--psm 7 -c tessedit_char_whitelist=0123456789.').strip()
                clean = raw.replace(".","").rjust(5)
                if len(clean) == 5:
                    for i in range(5):
                        if clean[i] not in self.patterns[str(i)]: self.patterns[str(i)][clean[i]] = []
                        self.patterns[str(i)][clean[i]].append((self.get_bin(self.zones[i], self.threshold)//255).tolist())
                print(f"\rCaptured: {[len(v) for v in self.patterns.values()]}", end="")
                time.sleep(self.interval / 1000.0)

            # STAGE 4: AUDIT & REFINEMENT
            self.audit_logic()

            # STAGE 5: INTERACTIVE TRAINING
            temp_config = self.build_fuzzy()
            print("\nSTAGE 5: INTERACTIVE REFINEMENT")
            print("Arrows: Left/Right to select slot, Up/Down to change digit.\n[TAB] Rebuild Engine | [ENTER] Continue")
            user_digits = [" ","1","2","0","0"]
            cursor = 2
            while not (win32api.GetAsyncKeyState(0x0D) & 0x8000):
                self.cls()
                bpm_str, cert, engine_res = self.recognize_current_bpm(temp_config)
                print(f"Engine Thinks: {bpm_str} ({int(cert*100)}%)")
                
                # UI Rendering
                nav_view = [f"[{d}]" if i == cursor else f" {d} " for i, d in enumerate(user_digits)]
                nav_view.insert(3, ".")
                print(f"User Corrects To: {''.join(nav_view)}")
                
                if win32api.GetAsyncKeyState(0x25) & 0x8000: cursor = max(0, cursor-1); time.sleep(0.15)
                if win32api.GetAsyncKeyState(0x27) & 0x8000: cursor = min(4, cursor+1); time.sleep(0.15)
                if win32api.GetAsyncKeyState(0x26) & 0x8000: # Up
                    v = user_digits[cursor]
                    user_digits[cursor] = "0" if v == " " else str((int(v)+1)%10); time.sleep(0.15)
                if win32api.GetAsyncKeyState(0x28) & 0x8000: # Down
                    v = user_digits[cursor]
                    user_digits[cursor] = " " if v == "0" else str((int(v)-1) if v != " " else "9"); time.sleep(0.15)
                
                if win32api.GetAsyncKeyState(0x09) & 0x8000: # TAB: Inject & Rebuild
                    for i in range(5):
                        char = user_digits[i]
                        if char not in self.patterns[str(i)]: self.patterns[str(i)][char] = []
                        self.patterns[str(i)][char].append((self.get_bin(self.zones[i], self.threshold)//255).tolist())
                    temp_config = self.build_fuzzy()
                    print("\nEngine Rebuilt!"); time.sleep(0.5)
                time.sleep(0.05)

            # STAGE 6: FINAL VERIFICATION
            self.config = temp_config
            self.cls()
            print("STAGE 6: FINAL VERIFICATION\n[ENTER] Finish & Save | [TAB] SCRAP AND RESTART ENTIRE SETUP")
            while True:
                bpm, cert, _ = self.recognize_current_bpm()
                print(f"\rTesting Live: {bpm} ({int(cert*100)}%)   ", end="")
                if win32api.GetAsyncKeyState(0x0D) & 0x8000: # Save
                    with open(filename, "w") as f: json.dump(self.config, f)
                    print("\nSaved!"); return
                if win32api.GetAsyncKeyState(0x09) & 0x8000: # Restart
                    self.patterns = {str(i): {} for i in range(5)}
                    break
                time.sleep(0.05)

    def audit_logic(self):
        time.sleep(0.5)
        for i in range(5):
            for char in self.needed:
                while char not in self.patterns[str(i)]:
                    self.cls()
                    print(f"AUDIT: Slot {i} needs '{char}'\n[TAB] Capture | [LEFT] Skip")
                    f = self.get_bin(self.zones[i], self.threshold)
                    self.draw_1to1(f)
                    if win32api.GetAsyncKeyState(0x09) & 0x8000:
                        self.patterns[str(i)][char] = [(f//255).tolist()]; time.sleep(0.4); break
                    if win32api.GetAsyncKeyState(0x25) & 0x8000: time.sleep(0.4); break
                    time.sleep(0.05)

    def build_fuzzy(self):
        magic = {}
        for pos, digits in self.patterns.items():
            magic[pos] = {}
            for char, vars in digits.items():
                if not vars: continue
                avg = np.mean([np.array(v) for v in vars], axis=0)
                y_on, x_on = np.where(avg > 0.7)
                y_off, x_off = np.where(avg < 0.3)
                samples = [[int(y_on[j]), int(x_on[j]), 1] for j in range(min(30, len(y_on)))]
                samples += [[int(y_off[j]), int(x_off[j]), 0] for j in range(min(30, len(y_off)))]
                magic[pos][char] = samples
        return {"zones": self.zones, "magic_pixels": magic, "threshold": self.threshold}

    def wait_key(self, k):
        while not (win32api.GetAsyncKeyState(k) & 0x8000): time.sleep(0.01)
        p = win32api.GetCursorPos(); time.sleep(0.5); return p

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--setup", action="store_true")
    p.add_argument("--config", default="bpm_config.json")
    p.add_argument("--write-bpm")
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--max-jump", type=float, default=5.0)
    args = p.parse_args()
    if args.setup: BPMWizard(args.interval).run_setup(args.config)
    else: BPMEngine(args.config).run_live(args.write_bpm, args.interval, args.max_jump)