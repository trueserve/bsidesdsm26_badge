#!/usr/bin/env python3
"""
BSides DSM 2026 Badge — Flashing Station GUI.

A kiosk-style pygame interface around the CH585 auto-flasher. It continuously
watches for a badge in the WCH USB bootloader and flashes the current firmware
the moment one appears, then waits for the board to disconnect before re-arming
so each badge is flashed exactly once.

Workflow at the booth:
  1. Person pulls the battery (or unplugs) to power-cycle their badge into the
     bootloader, then connects USB.
  2. The station detects the bootloader, flashes, and shows a big PASS/FAIL.
  3. Person disconnects; the station re-arms for the next badge.

Keys:
  TAB switch between FLASH and VALIDATE modes
  B   rebuild firmware (make build)
  C   clear the log / reset counters
  Q / Esc  quit

VALIDATE mode:
  The badge only reports its state when the player PRESSES THE BUTTON (PB23).
  Connect the badge over USB, have them press/hold the button, and the station
  reads the serial state and shows which of the 8 markers + the puzzle are done.
"""

import glob
import os
import queue
import re
import subprocess
import sys
import threading
import time

import pygame

try:
    import serial  # pyserial
except ImportError:  # pragma: no cover
    serial = None

HERE = os.path.dirname(os.path.abspath(__file__))
MINICHLINK = os.path.join(HERE, "ch32fun", "minichlink", "minichlink")
FIRMWARE_BIN = os.path.join(HERE, "bsidesdsmbadge.bin")

POLL_INTERVAL = 0.5  # seconds between bootloader probes

# --- Validation -------------------------------------------------------------
SERIAL_GLOB = "/dev/cu.usbmodem*"  # badge CDC port when running the app
BAUD = 115200                      # CDC ignores baud, but pyserial needs one

# (name, bit) for the 8 NFC markers, in bit order.
MARKERS = [
    ("HW_VILLAGE", 0x01),
    ("TALKS1", 0x02),
    ("TALKS2", 0x04),
    ("SOLDER_VILLAGE", 0x08),
    ("BLUE_TEAM", 0x10),
    ("VENDOR", 0x20),
    ("CTF", 0x40),
    ("CHECKIN", 0x80),
]

# Matches the badge's serial line:  "  foundTagHash: 1  markersFound: ff"
STATE_RE = re.compile(
    r"foundTagHash:\s*([0-9a-fA-F]+)\s+markersFound:\s*([0-9a-fA-F]+)"
)

# --- Colors ------------------------------------------------------------------
BG = (16, 18, 24)
PANEL = (26, 29, 38)
FG = (230, 233, 240)
MUTED = (140, 146, 160)
ACCENT = (90, 160, 255)
GREEN = (60, 200, 120)
AMBER = (240, 190, 70)
RED = (235, 90, 90)
PURPLE = (170, 130, 240)


class FlasherWorker(threading.Thread):
    """Background thread: probe for bootloader, flash, re-arm. Emits events."""

    def __init__(self, events: "queue.Queue"):
        super().__init__(daemon=True)
        self.events = events
        self.armed = True
        self.running = True
        self.busy = False
        self.flash_count = 0
        self.fail_count = 0
        self.mode = "FLASH"        # "FLASH" or "VALIDATE"
        self.last_validation = None
        self._ser = None
        self._ser_port = None

    # -- helpers --
    def emit(self, kind, **data):
        self.events.put({"kind": kind, **data})

    def log(self, msg):
        self.emit("log", text=msg, ts=time.strftime("%H:%M:%S"))

    def bootloader_present(self) -> bool:
        try:
            out = subprocess.run(
                [MINICHLINK, "-l"],
                capture_output=True, text=True, timeout=8,
            )
            return "Found MCU in bootloader mode" in (out.stdout + out.stderr)
        except Exception as e:  # noqa: BLE001
            self.log(f"probe error: {e}")
            return False

    def do_flash(self) -> bool:
        self.busy = True
        self.emit("state", state="FLASHING")
        self.log("Bootloader detected — flashing...")
        try:
            proc = subprocess.run(
                [MINICHLINK, "-w", FIRMWARE_BIN, "flash", "-b"],
                capture_output=True, text=True, timeout=60,
            )
            ok = proc.returncode == 0 and "Image written" in (proc.stdout + proc.stderr)
            for line in (proc.stdout + proc.stderr).splitlines():
                line = line.strip()
                if line:
                    self.log(line)
            if ok:
                self.flash_count += 1
                self.log("FLASH OK")
            else:
                self.fail_count += 1
                self.log(f"FLASH FAILED (rc={proc.returncode})")
            return ok
        except Exception as e:  # noqa: BLE001
            self.fail_count += 1
            self.log(f"FLASH ERROR: {e}")
            return False
        finally:
            self.busy = False

    def rebuild(self):
        self.emit("state", state="BUILDING")
        self.log("Rebuilding firmware (make build)...")
        try:
            proc = subprocess.run(
                ["make", "build"], cwd=HERE,
                capture_output=True, text=True, timeout=300,
            )
            if proc.returncode == 0:
                size = os.path.getsize(FIRMWARE_BIN) if os.path.exists(FIRMWARE_BIN) else 0
                self.log(f"Build OK ({size} bytes)")
            else:
                tail = (proc.stdout + proc.stderr).splitlines()[-6:]
                for line in tail:
                    self.log(line.strip())
                self.log("Build FAILED")
        except Exception as e:  # noqa: BLE001
            self.log(f"Build error: {e}")

    # -- mode switching --
    def set_mode(self, mode):
        if mode == self.mode:
            return
        self.mode = mode
        self.armed = True
        self.last_validation = None
        self.emit("mode", mode=mode)
        if mode == "FLASH":
            self.close_serial()
            self.log("Switched to FLASH mode.")
            self.emit("state", state="WAITING")
        else:
            self.log("Switched to VALIDATE mode — have the player press the button.")
            self.emit("state", state="VALIDATE_NOPORT")

    # -- serial helpers (validate mode) --
    def find_serial_port(self):
        ports = sorted(glob.glob(SERIAL_GLOB))
        return ports[0] if ports else None

    def open_serial(self, port):
        self.close_serial()
        try:
            self._ser = serial.Serial(port, BAUD, timeout=0.5)
            self._ser_port = port
            self.log(f"Validate: listening on {port}")
            self.emit("state", state="VALIDATE_WAIT")
        except Exception as e:  # noqa: BLE001
            self.log(f"open serial failed: {e}")
            self._ser = None
            self._ser_port = None

    def close_serial(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:  # noqa: BLE001
                pass
        self._ser = None
        self._ser_port = None

    def handle_validation(self, found_hash, markers):
        have = [name for name, bit in MARKERS if markers & bit]
        missing = [name for name, bit in MARKERS if not (markers & bit)]
        ok = markers == 0xFF and found_hash != 0
        self.last_validation = {
            "ok": ok,
            "markers": markers,
            "found_hash": found_hash,
            "have": have,
            "missing": missing,
        }
        self.emit("validate", **self.last_validation)
        self.emit("state", state="VALIDATE_PASS" if ok else "VALIDATE_FAIL")
        self.log(
            f"Validate: markers={markers:#04x} ({len(have)}/8) "
            f"hash={found_hash:#x} -> {'PASS' if ok else 'INCOMPLETE'}"
        )

    # -- per-tick handlers --
    def flash_tick(self):
        if self._ser is not None:
            self.close_serial()
        present = self.bootloader_present()
        if present:
            if self.armed:
                ok = self.do_flash()
                self.emit("result", ok=ok,
                          flashed=self.flash_count, failed=self.fail_count)
                self.armed = False
                self.emit("state", state="REMOVE")
                self.log("Done — remove badge (pull battery / unplug).")
        else:
            if not self.armed:
                self.armed = True
                self.log("Badge removed — re-armed for next.")
                self.emit("state", state="WAITING")
        time.sleep(POLL_INTERVAL)

    def validate_tick(self):
        if serial is None:
            self.log("pyserial not installed — run: pip3 install pyserial")
            time.sleep(1.0)
            return
        port = self.find_serial_port()
        if not port:
            if self._ser is not None:
                self.close_serial()
                self.emit("state", state="VALIDATE_NOPORT")
            time.sleep(POLL_INTERVAL)
            return
        if self._ser is None or self._ser_port != port:
            self.open_serial(port)
        if self._ser is None:
            time.sleep(POLL_INTERVAL)
            return
        try:
            raw = self._ser.readline()
        except Exception as e:  # noqa: BLE001
            self.log(f"serial error: {e}")
            self.close_serial()
            self.emit("state", state="VALIDATE_NOPORT")
            return
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            return
        m = STATE_RE.search(line)
        if m:
            self.handle_validation(int(m.group(1), 16), int(m.group(2), 16))
        elif "Badge State" in line:
            self.emit("state", state="VALIDATE_READING")

    # -- main loop --
    def run(self):
        if not os.path.exists(MINICHLINK):
            self.log("minichlink not found — build it: make -C ch32fun/minichlink")
        if not os.path.exists(FIRMWARE_BIN):
            self.log("firmware .bin missing — press B to build")
        self.emit("state", state="WAITING")
        while self.running:
            if self.mode == "FLASH":
                self.flash_tick()
            else:
                self.validate_tick()

    def stop(self):
        self.running = False
        self.close_serial()


def draw_text(surf, font, text, pos, color=FG):
    surf.blit(font.render(text, True, color), pos)


def main():
    pygame.init()
    pygame.display.set_caption("BSides DSM 2026 — Badge Flashing Station")
    W, H = 900, 600
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    f_big = pygame.font.SysFont("Menlo,Monaco,Consolas", 56, bold=True)
    f_mid = pygame.font.SysFont("Menlo,Monaco,Consolas", 26, bold=True)
    f_sml = pygame.font.SysFont("Menlo,Monaco,Consolas", 16)
    f_log = pygame.font.SysFont("Menlo,Monaco,Consolas", 14)

    events: "queue.Queue" = queue.Queue()
    worker = FlasherWorker(events)
    worker.start()

    state = "WAITING"
    mode = "FLASH"
    last_result = None  # True / False / None
    last_validation = None
    log_lines = []  # list of (ts, text)
    MAX_LOG = 200

    state_styles = {
        "WAITING":  (AMBER, "WAITING FOR BADGE"),
        "FLASHING": (ACCENT, "FLASHING..."),
        "BUILDING": (PURPLE, "BUILDING FIRMWARE"),
        "REMOVE":   (GREEN, "REMOVE BADGE"),
        "PASS":     (GREEN, "FLASH COMPLETE"),
        "FAIL":     (RED, "FLASH FAILED"),
        "VALIDATE_NOPORT":  (MUTED, "CONNECT BADGE"),
        "VALIDATE_WAIT":    (AMBER, "PRESS THE BUTTON"),
        "VALIDATE_READING": (ACCENT, "READING..."),
        "VALIDATE_PASS":    (GREEN, "SOLVE VALID"),
        "VALIDATE_FAIL":    (RED, "NOT COMPLETE"),
    }

    running = True
    while running:
        # --- drain worker events ---
        try:
            while True:
                ev = events.get_nowait()
                if ev["kind"] == "state":
                    state = ev["state"]
                elif ev["kind"] == "mode":
                    mode = ev["mode"]
                elif ev["kind"] == "log":
                    log_lines.append((ev.get("ts", ""), ev["text"]))
                    if len(log_lines) > MAX_LOG:
                        log_lines = log_lines[-MAX_LOG:]
                elif ev["kind"] == "result":
                    last_result = ev["ok"]
                    state = "PASS" if ev["ok"] else "FAIL"
                elif ev["kind"] == "validate":
                    last_validation = ev
        except queue.Empty:
            pass

        # --- input ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_TAB:
                    worker.set_mode("VALIDATE" if mode == "FLASH" else "FLASH")
                elif event.key == pygame.K_b:
                    threading.Thread(target=worker.rebuild, daemon=True).start()
                elif event.key == pygame.K_c:
                    log_lines.clear()
                    worker.flash_count = 0
                    worker.fail_count = 0
                    last_result = None
                    last_validation = None

        # --- draw ---
        screen.fill(BG)

        # Header
        draw_text(screen, f_mid, "BSides DSM 2026  ·  Badge Station", (24, 18), FG)
        mode_color = GREEN if mode == "VALIDATE" else ACCENT
        mtw = f_mid.size(f"[{mode}]")[0]
        draw_text(screen, f_mid, f"[{mode}]", (W - 24 - mtw, 18), mode_color)
        if mode == "FLASH":
            draw_text(screen, f_sml,
                      "Pull battery / unplug to reset into bootloader, then connect USB.",
                      (24, 52), MUTED)
        else:
            draw_text(screen, f_sml,
                      "Connect badge over USB — player must PRESS THE BUTTON to report state.",
                      (24, 52), MUTED)

        # Big status banner
        color, label = state_styles.get(state, (FG, state))
        banner = pygame.Rect(24, 86, W - 48, 150)
        pygame.draw.rect(screen, PANEL, banner, border_radius=14)
        pygame.draw.rect(screen, color, banner, width=3, border_radius=14)
        tw = f_big.size(label)[0]
        draw_text(screen, f_big, label, (banner.centerx - tw // 2, banner.y + 44), color)

        if mode == "FLASH":
            # Counters
            cy = 256
            draw_text(screen, f_mid, f"Flashed: {worker.flash_count}", (24, cy), GREEN)
            draw_text(screen, f_mid, f"Failed: {worker.fail_count}", (260, cy), RED if worker.fail_count else MUTED)
            bin_ok = os.path.exists(FIRMWARE_BIN)
            size = os.path.getsize(FIRMWARE_BIN) if bin_ok else 0
            draw_text(screen, f_sml,
                      f"firmware: {'bsidesdsmbadge.bin' if bin_ok else 'MISSING'}"
                      f"{f'  ({size} B)' if bin_ok else ''}",
                      (480, cy + 8), FG if bin_ok else RED)

            # Log panel
            log_panel = pygame.Rect(24, 300, W - 48, 252)
            pygame.draw.rect(screen, PANEL, log_panel, border_radius=10)
            ly = log_panel.y + 10
            visible = log_lines[-15:]
            for ts, text in visible:
                line = f"{ts}  {text}" if ts else text
                lc = FG
                low = text.lower()
                if "ok" in low or "written" in low or "complete" in low:
                    lc = GREEN
                elif "fail" in low or "error" in low:
                    lc = RED
                draw_text(screen, f_log, line[:96], (log_panel.x + 12, ly), lc)
                ly += 16
        else:
            # --- VALIDATE view ---
            draw_text(screen, f_mid, "Have the player PRESS & HOLD the button", (24, 252), AMBER)
            panel = pygame.Rect(24, 290, W - 48, 262)
            pygame.draw.rect(screen, PANEL, panel, border_radius=10)
            v = last_validation
            if v:
                col_w = (panel.width - 24) // 2
                for i, (name, bit) in enumerate(MARKERS):
                    have = bool(v["markers"] & bit)
                    cx = panel.x + 16 + (i % 2) * col_w
                    ry = panel.y + 14 + (i // 2) * 28
                    mark = "[x]" if have else "[ ]"
                    draw_text(screen, f_sml, f"{mark} {name}", (cx, ry), GREEN if have else RED)
                hy = panel.y + 14 + 4 * 28 + 8
                hash_ok = v["found_hash"] != 0
                draw_text(screen, f_sml,
                          f"{'[x]' if hash_ok else '[ ]'} LED / string puzzle"
                          f"  (foundTagHash={v['found_hash']:#x})",
                          (panel.x + 16, hy), GREEN if hash_ok else RED)
                verdict = "PASS — fully solved" if v["ok"] else "INCOMPLETE"
                draw_text(screen, f_mid,
                          f"Markers {len(v['have'])}/8     {verdict}",
                          (panel.x + 16, hy + 30), GREEN if v["ok"] else RED)
            else:
                draw_text(screen, f_sml,
                          "Waiting for the first button press...",
                          (panel.x + 16, panel.y + 16), MUTED)

        # Footer / keys
        draw_text(screen, f_sml, "[TAB] flash/validate   [B] rebuild   [C] clear   [Q] quit",
                  (24, H - 28), MUTED)

        pygame.display.flip()
        clock.tick(30)

    worker.stop()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
