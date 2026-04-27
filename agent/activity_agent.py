"""
Activity Ledger Agent - Lightweight activity tracker for Windows.

Captures all foreground window activity and AFK (idle) status,
then syncs to the ActivityLedger backend via the stateless webhook.
Replaces ActivityWatch as the data source.
"""

import json
import os
import sys
import time
import signal
import hashlib
import base64
import logging
import socket
import ctypes
import ctypes.wintypes as wintypes
import subprocess
import re
import atexit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from ctypes import Structure, c_uint, sizeof, byref
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
# When bundled as exe by PyInstaller, sys.executable is the exe path.
# When running as .py, __file__ is the script path.
if getattr(sys, "frozen", False):
    AGENT_DIR = Path(sys.executable).parent.resolve()
else:
    AGENT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = AGENT_DIR / "config.json"
DEFAULT_CONFIG = {
    "developer_id": "",
    "server_url": "https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook",
    "master_secret": "",
    "capture_interval_seconds": 30,
    "sync_interval_seconds": 300,
    "afk_timeout_seconds": 180,
    "queue_file": str(AGENT_DIR / "pending_events.json"),
    "log_file": str(AGENT_DIR / "activity_agent.log"),
    "max_queue_size": 10000,
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found at {CONFIG_FILE}")
        print("Run install.bat first or create config.json manually.")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)
    merged = {**DEFAULT_CONFIG, **cfg}
    if not merged["developer_id"]:
        print("ERROR: developer_id is empty in config.json")
        sys.exit(1)
    if not merged["master_secret"]:
        print("ERROR: master_secret is empty in config.json")
        sys.exit(1)
    return merged


def setup_logging(config: dict) -> logging.Logger:
    logger = logging.getLogger("activity_agent")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        config["log_file"], maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(handler)
    return logger


# ---------------------------------------------------------------------------
# Single Instance Lock (Windows Mutex)
# ---------------------------------------------------------------------------
def check_single_instance():
    """Prevent multiple agent instances via a named Windows mutex."""
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ActivityLedgerAgent_Mutex")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("Another instance of Activity Agent is already running. Exiting.")
        sys.exit(0)
    return mutex  # Must keep reference alive


# ---------------------------------------------------------------------------
# Token Generation (matches backend/stateless_webhook.py)
# ---------------------------------------------------------------------------
_cached_token = None
_cached_year = None


def generate_token(developer_id: str, master_secret: str) -> str:
    global _cached_token, _cached_year
    current_year = datetime.now().year
    if _cached_token and _cached_year == current_year:
        return _cached_token
    token_input = f"{developer_id}:{master_secret}:{current_year}"
    token_hash = hashlib.sha256(token_input.encode()).hexdigest()
    token_bytes = bytes.fromhex(token_hash[:48])
    _cached_token = base64.urlsafe_b64encode(token_bytes).decode().rstrip("=")
    _cached_year = current_year
    return _cached_token


# ---------------------------------------------------------------------------
# Win32 API — Active Window Info
# ---------------------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

# Titles to ignore (system/lock screens)
SKIP_TITLES = frozenset([
    "", "program manager", "task switching", "task view",
    "windows default lock screen", "lock screen", "new tab", "blank",
])


def get_active_window_info():
    """Return {"app": "app.exe", "title": "Window Title"} or None."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        # Window title
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return None
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()

        if title.lower() in SKIP_TITLES:
            return None

        # Process ID → exe name
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return None

        handle = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
        )
        if not handle:
            return {"app": "Unknown", "title": title}

        exe_buf = ctypes.create_unicode_buffer(260)
        psapi.GetModuleFileNameExW(handle, None, exe_buf, 260)
        kernel32.CloseHandle(handle)

        exe_path = exe_buf.value
        app_name = os.path.basename(exe_path) if exe_path else "Unknown"

        return {"app": app_name, "title": title}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# IDE Project Folder Detection (from process command line)
# ---------------------------------------------------------------------------
IDE_PROCESS_NAMES = {'code.exe', 'cursor.exe'}
_ide_project_cache = {}  # {app_lower: {"project": str, "time": float}}


def _get_ide_project_folder(app_name):
    """Get project folder name from IDE process command line. Cached for 5 min."""
    app_lower = (app_name or "").lower()
    if app_lower not in IDE_PROCESS_NAMES:
        return None

    # Check cache (valid for 5 minutes)
    cached = _ide_project_cache.get(app_lower)
    if cached and time.time() - cached["time"] < 300:
        return cached["project"]

    try:
        result = subprocess.run(
            ['wmic', 'process', 'where', f"Name='{app_lower}'",
             'get', 'CommandLine', '/VALUE'],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if not line.startswith('CommandLine='):
                continue
            cmdline = line[len('CommandLine='):]
            if '--type=' in cmdline:
                continue  # Skip renderer/GPU/utility processes

            # Extract folder paths: "exe_path" "folder_path"
            paths = re.findall(r'"([A-Za-z]:\\[^"]+)"', cmdline)
            for path in paths[1:]:  # Skip first path (exe)
                if os.path.isdir(path):
                    project = os.path.basename(path)
                    _ide_project_cache[app_lower] = {"project": project, "time": time.time()}
                    return project

        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Win32 API — Idle / AFK Detection
# ---------------------------------------------------------------------------
class LASTINPUTINFO(Structure):
    _fields_ = [("cbSize", c_uint), ("dwTime", c_uint)]


def get_idle_seconds() -> float:
    """Return seconds since last keyboard/mouse input."""
    lii = LASTINPUTINFO()
    lii.cbSize = sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(byref(lii)):
        return 0.0
    tick_count = kernel32.GetTickCount()
    elapsed_ms = tick_count - lii.dwTime
    # Handle tick count rollover (every ~49 days)
    if elapsed_ms < 0:
        elapsed_ms += 0xFFFFFFFF
    return elapsed_ms / 1000.0


def is_screen_locked() -> bool:
    """Check if Windows is on lock screen or display is off."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return True
        # Check if foreground process is LockApp or LogonUI (lock screen)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == 0:
            return False
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value
        )
        if not handle:
            return False
        exe_buf = ctypes.create_unicode_buffer(260)
        psapi.GetModuleFileNameExW(handle, None, exe_buf, 260)
        kernel32.CloseHandle(handle)
        exe_name = os.path.basename(exe_buf.value).lower()
        return exe_name in ('lockapp.exe', 'logonui.exe')
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Window Session Tracker
# ---------------------------------------------------------------------------
class WindowTracker:
    def __init__(self, afk_timeout: float):
        self.afk_timeout = afk_timeout

        # Current window session
        self.current_app = None
        self.current_title = None
        self.current_project = None
        self.session_start = None

        # Smart AFK: track when screen content last changed
        # (prevents false AFK when using AI tools like Claude Code)
        self.last_screen_change = datetime.now(timezone.utc)

        # AFK state
        self.afk_state = "not-afk"
        self.afk_start = None
        self.active_start = datetime.now(timezone.utc)

        # Accumulated events (drained at sync time)
        self.window_events = []
        self.afk_events = []

    def tick(self):
        """Called every capture interval. Captures current window + AFK state."""
        now = datetime.now(timezone.utc)
        idle_secs = get_idle_seconds()

        # --- Active window tracking (BEFORE AFK check) ---
        info = get_active_window_info()
        if info is not None:
            new_app = info["app"]
            new_title = info["title"]

            # If window changed, close previous session and open a new one
            if new_app != self.current_app or new_title != self.current_title:
                self.last_screen_change = now  # Screen content changed
                self._close_window_session(now)
                self.current_app = new_app
                self.current_title = new_title
                self.current_project = _get_ide_project_folder(new_app)
                self.session_start = now

        # --- AFK state machine (uses last_screen_change) ---
        self._update_afk(now, idle_secs)

    def _close_window_session(self, now):
        """Emit a completed window event."""
        if self.current_app and self.session_start:
            duration = (now - self.session_start).total_seconds()
            if duration >= 5:  # Backend skips < 5s
                event_data = {
                    "app": self.current_app,
                    "title": self.current_title or "",
                }
                if self.current_project:
                    event_data["project"] = self.current_project
                self.window_events.append({
                    "timestamp": self.session_start.isoformat(),
                    "duration": round(duration, 1),
                    "data": event_data,
                })

    def _update_afk(self, now, idle_secs):
        """Update AFK state machine and emit events on transitions.

        Smart AFK: If the screen content is actively changing (e.g. AI tool
        like Claude Code is making edits, files switching), the user is still
        engaged even without keyboard/mouse input. Don't mark as AFK.

        Hard cap: beyond 2× afk_timeout of physical inactivity, always mark
        AFK regardless of screen changes (prevents lunch breaks from being
        counted as work when AI tools are running in background).
        """
        secs_since_screen_change = (now - self.last_screen_change).total_seconds()
        screen_active = secs_since_screen_change < self.afk_timeout

        if self.afk_state == "not-afk" and idle_secs >= self.afk_timeout:
            # Only apply smart-AFK grace period if within 2× timeout.
            # Beyond that, the user is physically away (lunch break, etc.)
            if screen_active and idle_secs < self.afk_timeout * 2:
                return  # Screen content is changing — user is monitoring (AI tool, etc.)
            # ACTIVE → AFK
            afk_started = now - timedelta(seconds=idle_secs)
            if self.active_start:
                active_dur = (afk_started - self.active_start).total_seconds()
                if active_dur >= 1:
                    self.afk_events.append({
                        "timestamp": self.active_start.isoformat(),
                        "duration": round(active_dur, 1),
                        "data": {"status": "not-afk"},
                    })
            self.afk_state = "afk"
            self.afk_start = afk_started

        elif self.afk_state == "afk" and idle_secs < self.afk_timeout:
            # AFK → ACTIVE
            if self.afk_start:
                afk_dur = (now - self.afk_start).total_seconds()
                if afk_dur >= 1:
                    self.afk_events.append({
                        "timestamp": self.afk_start.isoformat(),
                        "duration": round(afk_dur, 1),
                        "data": {"status": "afk"},
                    })
            self.afk_state = "not-afk"
            self.active_start = now

    def flush_current(self):
        """Close the current window session and emit a not-afk event for ongoing active time."""
        now = datetime.now(timezone.utc)
        self._close_window_session(now)
        # Re-open session so tracking continues
        self.session_start = now

        # Emit a not-afk event for the current active period
        if self.afk_state == "not-afk" and self.active_start:
            dur = (now - self.active_start).total_seconds()
            if dur >= 1:
                self.afk_events.append({
                    "timestamp": self.active_start.isoformat(),
                    "duration": round(dur, 1),
                    "data": {"status": "not-afk"},
                })
            self.active_start = now

    def drain_events(self):
        """Return and clear accumulated events."""
        window = self.window_events[:]
        afk = self.afk_events[:]
        self.window_events.clear()
        self.afk_events.clear()
        return window, afk


# ---------------------------------------------------------------------------
# Sync Manager with Offline Queue
# ---------------------------------------------------------------------------
class SyncManager:
    def __init__(self, config: dict, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.hostname = socket.gethostname()
        self.queue_file = Path(config["queue_file"])
        self.max_queue = config.get("max_queue_size", 10000)
        self.pending_window = []
        self.pending_afk = []
        self._load_queue()

    def add_events(self, window_events, afk_events):
        self.pending_window.extend(window_events)
        self.pending_afk.extend(afk_events)
        # Trim if queue is too large
        total = len(self.pending_window) + len(self.pending_afk)
        if total > self.max_queue:
            excess = total - self.max_queue
            if len(self.pending_window) > excess:
                self.pending_window = self.pending_window[excess:]
            else:
                self.pending_window.clear()
                self.pending_afk = self.pending_afk[excess - len(self.pending_window):]

    def sync(self) -> bool:
        """Send pending events to the server. Returns True on success."""
        if not self.pending_window and not self.pending_afk:
            return True

        payload = {}
        if self.pending_window:
            payload[f"aw-watcher-window_{self.hostname}"] = self.pending_window
        if self.pending_afk:
            payload[f"aw-watcher-afk_{self.hostname}"] = self.pending_afk

        token = generate_token(self.config["developer_id"], self.config["master_secret"])
        headers = {
            "Developer-ID": self.config["developer_id"],
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            import requests

            resp = requests.post(
                self.config["server_url"],
                json=payload,
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()
                self.logger.info(
                    f"Synced: {result.get('processed', 0)} activities, "
                    f"{result.get('duplicates_skipped', 0)} dupes skipped"
                )
                self.pending_window.clear()
                self.pending_afk.clear()
                self._save_queue()
                return True
            else:
                self.logger.error(f"Server returned {resp.status_code}: {resp.text[:200]}")
                self._save_queue()
                return False
        except Exception as e:
            self.logger.error(f"Sync failed (will retry): {e}")
            self._save_queue()
            return False

    def _save_queue(self):
        try:
            data = {"window": self.pending_window, "afk": self.pending_afk}
            self.queue_file.write_text(json.dumps(data), encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to save queue: {e}")

    def _load_queue(self):
        if self.queue_file.exists():
            try:
                data = json.loads(self.queue_file.read_text(encoding="utf-8"))
                self.pending_window = data.get("window", [])
                self.pending_afk = data.get("afk", [])
                if self.pending_window or self.pending_afk:
                    self.logger.info(
                        f"Loaded queue: {len(self.pending_window)} window + "
                        f"{len(self.pending_afk)} AFK events"
                    )
            except Exception as e:
                self.logger.error(f"Failed to load queue: {e}")


# ---------------------------------------------------------------------------
# Main Agent
# ---------------------------------------------------------------------------
class ActivityAgent:
    def __init__(self):
        self.config = load_config()
        self.logger = setup_logging(self.config)
        self.tracker = WindowTracker(afk_timeout=self.config["afk_timeout_seconds"])
        self.sync_mgr = SyncManager(self.config, self.logger)
        self.running = True
        self.last_sync = time.time()
        self.last_tick_time = time.time()
        self.idle_paused = False

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        atexit.register(self._on_exit)

    def _shutdown(self, signum, frame):
        self.logger.info(f"Shutdown signal {signum} received")
        self.running = False

    def _on_exit(self):
        """Save any pending events before exit."""
        self.tracker.flush_current()
        window_events, afk_events = self.tracker.drain_events()
        self.sync_mgr.add_events(window_events, afk_events)
        self.sync_mgr._save_queue()
        self.logger.info("Saved pending events on exit")

    def run(self):
        self.logger.info("=" * 50)
        self.logger.info("Activity Agent started")
        self.logger.info(f"Developer: {self.config['developer_id']}")
        self.logger.info(f"Server: {self.config['server_url']}")
        self.logger.info(
            f"Capture: {self.config['capture_interval_seconds']}s, "
            f"Sync: {self.config['sync_interval_seconds']}s, "
            f"AFK timeout: {self.config['afk_timeout_seconds']}s"
        )

        while self.running:
            try:
                # --- Sleep/hibernate detection ---
                # If wall-clock gap >> capture interval, the PC was suspended.
                # Close the open window session at the moment of sleep (not now)
                # and record an AFK event for the entire gap so the time isn't
                # counted as active work.
                now_wall = time.time()
                gap = now_wall - self.last_tick_time
                sleep_threshold = self.config["capture_interval_seconds"] + 60
                if gap > sleep_threshold:
                    sleep_start_dt = datetime.fromtimestamp(
                        self.last_tick_time, tz=timezone.utc
                    )
                    wake_dt = datetime.fromtimestamp(now_wall, tz=timezone.utc)
                    self.logger.info(
                        f"Sleep/hibernate detected — {gap:.0f}s gap "
                        f"({sleep_start_dt.strftime('%H:%M:%S')} UTC → "
                        f"{wake_dt.strftime('%H:%M:%S')} UTC)"
                    )
                    if not self.idle_paused:
                        # Close any open window session up to the sleep moment
                        self.tracker._close_window_session(sleep_start_dt)
                        self.tracker.current_app = None
                        self.tracker.current_title = None
                        self.tracker.current_project = None
                        self.tracker.session_start = None
                        # Emit not-afk for the active period that ended at sleep
                        if self.tracker.afk_state == "not-afk" and self.tracker.active_start:
                            active_dur = (sleep_start_dt - self.tracker.active_start).total_seconds()
                            if active_dur >= 1:
                                self.tracker.afk_events.append({
                                    "timestamp": self.tracker.active_start.isoformat(),
                                    "duration": round(active_dur, 1),
                                    "data": {"status": "not-afk"},
                                })
                        # Emit AFK event covering the entire sleep gap
                        self.tracker.afk_events.append({
                            "timestamp": sleep_start_dt.isoformat(),
                            "duration": round(gap, 1),
                            "data": {"status": "afk"},
                        })
                        self.tracker.afk_state = "afk"
                        self.tracker.afk_start = wake_dt
                        self.idle_paused = True
                self.last_tick_time = now_wall

                idle_secs = get_idle_seconds()
                screen_locked = is_screen_locked()
                afk_timeout = self.config["afk_timeout_seconds"]
                # Smart pause: if screen content is actively changing (e.g. Claude Code
                # editing files), developer is monitoring AI output — don't pause.
                # Hard cap: beyond 2× afk_timeout of physical inactivity, always
                # pause regardless of screen changes (prevents AI tools from
                # keeping the timer running during long breaks).
                screen_changing = (
                    (datetime.now(timezone.utc) - self.tracker.last_screen_change).total_seconds()
                    < afk_timeout
                )
                hard_afk = idle_secs >= afk_timeout * 2
                should_pause = screen_locked or hard_afk or (idle_secs >= afk_timeout and not screen_changing)

                if not self.idle_paused:
                    if should_pause:
                        # System idle / screen locked / display off — stop capturing
                        now_dt = datetime.now(timezone.utc)
                        afk_started = now_dt - timedelta(seconds=idle_secs)
                        if screen_locked:
                            self.logger.info("Screen locked — pausing activity capture")
                        else:
                            self.logger.info(
                                f"System idle ({idle_secs:.0f}s) — pausing activity capture"
                            )
                        # Close current window session
                        self.tracker.flush_current()
                        # Emit not-afk event for the active period that just ended
                        if self.tracker.afk_state == "not-afk" and self.tracker.active_start:
                            active_dur = (afk_started - self.tracker.active_start).total_seconds()
                            if active_dur >= 1:
                                self.tracker.afk_events.append({
                                    "timestamp": self.tracker.active_start.isoformat(),
                                    "duration": round(active_dur, 1),
                                    "data": {"status": "not-afk"},
                                })
                        self.tracker.afk_state = "afk"
                        self.tracker.afk_start = afk_started
                        # Clear window session so nothing new is tracked
                        self.tracker.current_app = None
                        self.tracker.current_title = None
                        self.tracker.current_project = None
                        self.tracker.session_start = None
                        self.idle_paused = True
                    else:
                        # System active — normal capture
                        self.tracker.tick()
                else:
                    # Currently paused — wait for user to return
                    if not should_pause:
                        # User is back — screen unlocked and keyboard/mouse active
                        now_dt = datetime.now(timezone.utc)
                        if self.tracker.afk_start:
                            afk_dur = (now_dt - self.tracker.afk_start).total_seconds()
                            if afk_dur >= 1:
                                self.tracker.afk_events.append({
                                    "timestamp": self.tracker.afk_start.isoformat(),
                                    "duration": round(afk_dur, 1),
                                    "data": {"status": "afk"},
                                })
                        self.tracker.afk_state = "not-afk"
                        self.tracker.active_start = now_dt
                        self.tracker.afk_start = None
                        self.tracker.last_screen_change = now_dt
                        self.idle_paused = False
                        self.logger.info("User activity detected — resuming capture")

                # Sync if interval elapsed (even when paused, to flush pending data)
                now = time.time()
                if now - self.last_sync >= self.config["sync_interval_seconds"]:
                    self.tracker.flush_current()
                    window_events, afk_events = self.tracker.drain_events()
                    self.sync_mgr.add_events(window_events, afk_events)

                    w_count = len(self.sync_mgr.pending_window)
                    a_count = len(self.sync_mgr.pending_afk)
                    if w_count > 0 or a_count > 0:
                        self.logger.info(f"Syncing {w_count} window + {a_count} AFK events...")
                        self.sync_mgr.sync()
                    self.last_sync = now

                # Sleep until next check
                time.sleep(self.config["capture_interval_seconds"])

            except Exception as e:
                self.logger.error(f"Main loop error: {e}", exc_info=True)
                time.sleep(5)

        self.logger.info("Activity Agent stopped")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mutex = check_single_instance()
    agent = ActivityAgent()
    agent.run()
