"""
Activity Ledger Agent - Lightweight activity tracker for Linux.

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
import subprocess
import fcntl
import atexit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
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
        print("Run install_linux.sh first or create config.json manually.")
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
# Single Instance Lock (File Lock)
# ---------------------------------------------------------------------------
_lock_file = None


def check_single_instance():
    """Prevent multiple agent instances via a file lock."""
    global _lock_file
    lock_path = AGENT_DIR / ".agent.lock"
    try:
        _lock_file = open(lock_path, "w")
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid()))
        _lock_file.flush()
    except (IOError, OSError):
        print("Another instance of Activity Agent is already running. Exiting.")
        sys.exit(0)
    return _lock_file


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
# Linux — Active Window Info (via xdotool / xprop)
# ---------------------------------------------------------------------------
SKIP_TITLES = frozenset([
    "", "program manager", "task switching", "task view",
    "windows default lock screen", "lock screen", "new tab", "blank",
    "desktop", "panel",
])


def _get_window_xdotool():
    """Get active window info using xdotool (X11)."""
    try:
        # Get active window ID
        wid_result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=5
        )
        if wid_result.returncode != 0:
            return None
        wid = wid_result.stdout.strip()

        # Get window title
        title_result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=5
        )
        title = title_result.stdout.strip() if title_result.returncode == 0 else ""

        # Get PID and app name
        pid_result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowpid"],
            capture_output=True, text=True, timeout=5
        )
        app_name = "Unknown"
        if pid_result.returncode == 0 and pid_result.stdout.strip():
            pid = pid_result.stdout.strip()
            comm_path = f"/proc/{pid}/comm"
            if os.path.exists(comm_path):
                with open(comm_path, "r") as f:
                    app_name = f.read().strip()

        return {"app": app_name, "title": title}
    except (subprocess.TimeoutExpired, Exception):
        return None


def _get_window_xprop():
    """Fallback: Get active window info using xprop (X11)."""
    try:
        # Get active window ID
        root_result = subprocess.run(
            ["xprop", "-root", "_NET_ACTIVE_WINDOW"],
            capture_output=True, text=True, timeout=5
        )
        if root_result.returncode != 0:
            return None

        # Parse window ID from output like: _NET_ACTIVE_WINDOW(WINDOW): window id # 0x1234567
        parts = root_result.stdout.strip().split()
        wid = parts[-1] if parts else None
        if not wid or wid == "0x0":
            return None

        # Get window title
        name_result = subprocess.run(
            ["xprop", "-id", wid, "WM_NAME"],
            capture_output=True, text=True, timeout=5
        )
        title = ""
        if name_result.returncode == 0 and '"' in name_result.stdout:
            title = name_result.stdout.split('"', 1)[1].rsplit('"', 1)[0]

        # Get app class name
        class_result = subprocess.run(
            ["xprop", "-id", wid, "WM_CLASS"],
            capture_output=True, text=True, timeout=5
        )
        app_name = "Unknown"
        if class_result.returncode == 0 and '"' in class_result.stdout:
            # WM_CLASS returns: "instance", "class" — we want the class (2nd value)
            parts = class_result.stdout.split('"')
            if len(parts) >= 4:
                app_name = parts[3]  # class name
            elif len(parts) >= 2:
                app_name = parts[1]  # instance name

        return {"app": app_name, "title": title}
    except (subprocess.TimeoutExpired, Exception):
        return None


def _get_window_gdbus():
    """Fallback for GNOME/Wayland: use gdbus to get window info."""
    try:
        result = subprocess.run(
            ["gdbus", "call", "--session",
             "--dest", "org.gnome.Shell",
             "--object-path", "/org/gnome/Shell",
             "--method", "org.gnome.Shell.Eval",
             "global.display.focus_window ? "
             "JSON.stringify({app: global.display.focus_window.get_wm_class(), "
             "title: global.display.focus_window.get_title()}) : 'null'"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None
        # Parse output: (true, '{"app":"firefox","title":"Page Title"}')
        output = result.stdout.strip()
        if "'null'" in output or "false" in output:
            return None
        # Extract JSON from gdbus output
        json_start = output.find("'{") + 1
        json_end = output.rfind("}'") + 1
        if json_start > 0 and json_end > json_start:
            json_str = output[json_start:json_end].replace("\\'", "'")
            data = json.loads(json_str)
            return {"app": data.get("app", "Unknown"), "title": data.get("title", "")}
        return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None


# Detect which method works on this system
_window_method = None


def get_active_window_info():
    """Return {"app": "AppName", "title": "Window Title"} or None."""
    global _window_method

    # Try cached method first
    if _window_method:
        result = _window_method()
        if result and result["title"].lower() not in SKIP_TITLES:
            return result

    # Try all methods in order of preference
    for method in [_get_window_xdotool, _get_window_xprop, _get_window_gdbus]:
        result = method()
        if result:
            _window_method = method  # Cache working method
            if result["title"].lower() not in SKIP_TITLES:
                return result
            return None

    return None


# ---------------------------------------------------------------------------
# Linux — Idle / AFK Detection
# ---------------------------------------------------------------------------
def _idle_xprintidle():
    """Get idle time using xprintidle (X11)."""
    try:
        result = subprocess.run(
            ["xprintidle"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip()) / 1000.0  # milliseconds to seconds
    except (subprocess.TimeoutExpired, ValueError, Exception):
        pass
    return None


def _idle_xssstate():
    """Get idle time using xssstate (X11, part of suckless-tools)."""
    try:
        result = subprocess.run(
            ["xssstate", "-i"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip()) / 1000.0  # milliseconds to seconds
    except (subprocess.TimeoutExpired, ValueError, Exception):
        pass
    return None


def _idle_dbus_gnome():
    """Get idle time using D-Bus (GNOME)."""
    try:
        result = subprocess.run(
            ["dbus-send", "--print-reply", "--dest=org.gnome.Mutter.IdleMonitor",
             "/org/gnome/Mutter/IdleMonitor/Core",
             "org.gnome.Mutter.IdleMonitor.GetIdletime"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("uint64"):
                    return int(line.split()[1]) / 1000.0  # milliseconds to seconds
    except (subprocess.TimeoutExpired, ValueError, Exception):
        pass
    return None


_idle_method = None


def get_idle_seconds() -> float:
    """Return seconds since last keyboard/mouse input."""
    global _idle_method

    # Try cached method first
    if _idle_method:
        result = _idle_method()
        if result is not None:
            return result

    # Try all methods
    for method in [_idle_xprintidle, _idle_xssstate, _idle_dbus_gnome]:
        result = method()
        if result is not None:
            _idle_method = method
            return result

    return 0.0  # Default: assume active


# ---------------------------------------------------------------------------
# Window Session Tracker
# ---------------------------------------------------------------------------
class WindowTracker:
    def __init__(self, afk_timeout: float):
        self.afk_timeout = afk_timeout

        self.current_app = None
        self.current_title = None
        self.session_start = None

        self.afk_state = "not-afk"
        self.afk_start = None
        self.active_start = datetime.now(timezone.utc)

        self.window_events = []
        self.afk_events = []

    def tick(self):
        now = datetime.now(timezone.utc)
        idle_secs = get_idle_seconds()

        self._update_afk(now, idle_secs)

        info = get_active_window_info()
        if info is None:
            return

        new_app = info["app"]
        new_title = info["title"]

        if new_app != self.current_app or new_title != self.current_title:
            self._close_window_session(now)
            self.current_app = new_app
            self.current_title = new_title
            self.session_start = now

    def _close_window_session(self, now):
        if self.current_app and self.session_start:
            duration = (now - self.session_start).total_seconds()
            if duration >= 5:
                self.window_events.append({
                    "timestamp": self.session_start.isoformat(),
                    "duration": round(duration, 1),
                    "data": {
                        "app": self.current_app,
                        "title": self.current_title or "",
                    },
                })

    def _update_afk(self, now, idle_secs):
        if self.afk_state == "not-afk" and idle_secs >= self.afk_timeout:
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
        now = datetime.now(timezone.utc)
        self._close_window_session(now)
        self.session_start = now

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
        total = len(self.pending_window) + len(self.pending_afk)
        if total > self.max_queue:
            excess = total - self.max_queue
            if len(self.pending_window) > excess:
                self.pending_window = self.pending_window[excess:]
            else:
                self.pending_window.clear()
                self.pending_afk = self.pending_afk[excess - len(self.pending_window):]

    def sync(self) -> bool:
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

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        atexit.register(self._on_exit)

    def _shutdown(self, signum, frame):
        self.logger.info(f"Shutdown signal {signum} received")
        self.running = False

    def _on_exit(self):
        self.tracker.flush_current()
        window_events, afk_events = self.tracker.drain_events()
        self.sync_mgr.add_events(window_events, afk_events)
        self.sync_mgr._save_queue()
        self.logger.info("Saved pending events on exit")

    def run(self):
        self.logger.info("=" * 50)
        self.logger.info("Activity Agent started (Linux)")
        self.logger.info(f"Developer: {self.config['developer_id']}")
        self.logger.info(f"Server: {self.config['server_url']}")
        self.logger.info(
            f"Capture: {self.config['capture_interval_seconds']}s, "
            f"Sync: {self.config['sync_interval_seconds']}s, "
            f"AFK timeout: {self.config['afk_timeout_seconds']}s"
        )

        while self.running:
            try:
                self.tracker.tick()

                now = time.time()
                if now - self.last_sync >= self.config["sync_interval_seconds"]:
                    self.tracker.flush_current()
                    window_events, afk_events = self.tracker.drain_events()
                    self.sync_mgr.add_events(window_events, afk_events)

                    w_count = len(self.sync_mgr.pending_window)
                    a_count = len(self.sync_mgr.pending_afk)
                    self.logger.info(f"Syncing {w_count} window + {a_count} AFK events...")
                    self.sync_mgr.sync()
                    self.last_sync = now

                time.sleep(self.config["capture_interval_seconds"])

            except Exception as e:
                self.logger.error(f"Main loop error: {e}", exc_info=True)
                time.sleep(5)

        self.logger.info("Activity Agent stopped")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    lock = check_single_instance()
    agent = ActivityAgent()
    agent.run()
