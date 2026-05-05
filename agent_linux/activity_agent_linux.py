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
    "shutdown_idle_seconds": 3600,
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

# ---------------------------------------------------------------------------
# IDE Project Folder Detection (from /proc/<pid>/cwd)
# ---------------------------------------------------------------------------
IDE_PROCESS_NAMES = {'code', 'cursor', 'code-oss'}
_ide_project_cache = {}  # {app_lower: {"project": str, "time": float}}


def _get_ide_project_folder(app_name):
    """Get project folder name from IDE process working directory. Cached for 5 min."""
    app_lower = (app_name or "").lower()
    if app_lower not in IDE_PROCESS_NAMES:
        return None

    # Check cache (valid for 5 minutes)
    cached = _ide_project_cache.get(app_lower)
    if cached and time.time() - cached["time"] < 300:
        return cached["project"]

    try:
        # Find PID of the main IDE process (not a helper/renderer)
        result = subprocess.run(
            ['pgrep', '-f', app_lower],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return None

        for pid in result.stdout.strip().split('\n'):
            pid = pid.strip()
            if not pid:
                continue
            cwd_link = f"/proc/{pid}/cwd"
            if os.path.islink(cwd_link):
                cwd = os.readlink(cwd_link)
                # Skip system dirs — we want project folders
                if cwd and cwd != '/' and not cwd.startswith('/usr'):
                    project = os.path.basename(cwd)
                    if project:
                        _ide_project_cache[app_lower] = {"project": project, "time": time.time()}
                        return project

        return None
    except Exception:
        return None


def get_active_window_info():
    """Return {"app": "AppName", "title": "Window Title"} or None."""
    global _window_method

    # Try cached method first
    if _window_method:
        result = _window_method()
        if result and result["title"].lower() not in SKIP_TITLES:
            # Add project folder from IDE process (if applicable)
            project = _get_ide_project_folder(result["app"])
            if project:
                result["project"] = project
            return result

    # Try all methods in order of preference
    for method in [_get_window_xdotool, _get_window_xprop, _get_window_gdbus]:
        result = method()
        if result:
            _window_method = method  # Cache working method
            if result["title"].lower() not in SKIP_TITLES:
                project = _get_ide_project_folder(result["app"])
                if project:
                    result["project"] = project
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


# AI coding CLI tools — when any of these are running the developer has
# delegated work to AI and is productively engaged even without keyboard input.
_AI_CODING_PROCS = ('claude', 'aider', 'codex', 'copilot', 'cody')
_AI_TOOL_DISPLAY = {
    'claude': 'Claude Code', 'aider': 'Aider',
    'codex': 'Codex', 'copilot': 'Copilot', 'cody': 'Cody',
}

# Terminal app names on Linux
_TERMINAL_APP_NAMES = frozenset([
    'gnome-terminal', 'gnome terminal', 'konsole', 'xterm',
    'terminator', 'tilix', 'xfce4-terminal', 'mate-terminal',
    'lxterminal', 'urxvt', 'st', 'alacritty', 'kitty', 'hyper',
])

# Cache: (tool_name, project) — refreshed every 30 s
_ai_tool_cache: dict = {"tool": None, "project": None, "ts": 0.0}


def _get_ai_tool_info() -> tuple:
    """Return (tool_name, project_folder) for a running AI coding tool, or (None, None).

    Reads the tool process's working directory via /proc/<pid>/cwd so the correct
    project is always captured even when the terminal title doesn't include it.
    Result is cached for 30 s to avoid repeated subprocess calls every tick.
    """
    global _ai_tool_cache
    now = time.time()
    if now - _ai_tool_cache["ts"] < 30:
        return _ai_tool_cache["tool"], _ai_tool_cache["project"]

    tool_name = None
    project = None
    for proc in _AI_CODING_PROCS:
        try:
            pid_r = subprocess.run(
                ["pgrep", "-x", proc], capture_output=True, text=True, timeout=2
            )
            if pid_r.returncode != 0:
                continue
            pid = pid_r.stdout.strip().split("\n")[0].strip()
            tool_name = proc
            # Read CWD from /proc (Linux-specific, fast, no extra process)
            import os as _os
            cwd_path = _os.readlink(f"/proc/{pid}/cwd")
            folder = cwd_path.rstrip("/").split("/")[-1]
            if folder and len(folder) > 2:
                project = folder
            break
        except Exception:
            continue

    _ai_tool_cache = {"tool": tool_name, "project": project, "ts": now}
    return tool_name, project


def is_claude_code_active() -> bool:
    """Return True if Claude Code or any other AI coding CLI tool is running."""
    tool, _ = _get_ai_tool_info()
    return tool is not None


# Window title keywords that indicate an AI tool or team chat.
# Used to keep idle state as 'productive' when reading AI responses.
AI_TOOL_TITLE_KEYWORDS: frozenset = frozenset([
    "claude",           # Claude.ai browser tab
    "chatgpt",          # ChatGPT
    "gemini",           # Google Gemini
    "google ai studio", # AI Studio
    "aistudio",         # AI Studio URL variant
    "perplexity",       # Perplexity AI
    "copilot",          # Microsoft / GitHub Copilot
    "grok",             # Grok AI
    "google chat",      # Google Chat
    "google meet",      # Google Meet
    "blackbox",         # Blackbox AI
])


def is_ai_tool_or_chat_active(current_title: str | None) -> bool:
    """Return True if the active window title matches an AI tool or team chat."""
    if not current_title:
        return False
    title_lower = current_title.lower()
    return any(kw in title_lower for kw in AI_TOOL_TITLE_KEYWORDS)


def is_screen_locked() -> bool:
    """Best-effort check if the Linux screen/session is locked."""
    # Try loginctl (systemd)
    try:
        result = subprocess.run(
            ["loginctl", "show-session", "-p", "LockedHint", "--value"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip().lower() == "yes"
    except Exception:
        pass
    # Try D-Bus screensaver (GNOME / KDE)
    try:
        result = subprocess.run(
            ["dbus-send", "--print-reply",
             "--dest=org.freedesktop.ScreenSaver",
             "/org/freedesktop/ScreenSaver",
             "org.freedesktop.ScreenSaver.GetActive"],
            capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0:
            return "true" in result.stdout.lower()
    except Exception:
        pass
    return False


_display_asleep_cache: dict = {"result": False, "ts": 0.0}


def is_display_asleep() -> bool:
    """Return True if all displays are off/sleeping on Linux (lid closed or DPMS off).

    Priority order:
    1. ACPI lid state via /proc/acpi/button/lid/*/state — direct lid sensor, fast.
    2. DPMS state via `xset q` — catches display sleep regardless of lid state.
    3. DRM connector status via /sys/class/drm/*/status — catches HDMI/DP disconnect.

    Result cached 5 s. Returns False when no lid sensor is found (desktop) so
    capture continues normally; idle timeout handles the AFK case on desktops.
    """
    global _display_asleep_cache
    now = time.time()
    if now - _display_asleep_cache["ts"] < 5:
        return _display_asleep_cache["result"]

    result = False

    # Method 1: ACPI lid state (works on most Linux laptops with ACPI)
    try:
        import glob as _glob
        lid_files = _glob.glob("/proc/acpi/button/lid/*/state")
        if lid_files:
            all_closed = True
            any_found = False
            for lid_file in lid_files:
                try:
                    with open(lid_file) as f:
                        state = f.read().strip()
                    any_found = True
                    if "open" in state.lower():
                        all_closed = False
                        break
                except Exception:
                    pass
            if any_found and all_closed:
                result = True
    except Exception:
        pass

    # Method 2: DPMS state via xset (X11 — catches display sleep/standby/off)
    if not result:
        try:
            xdisplay = os.environ.get("DISPLAY", ":0")
            proc = subprocess.run(
                ["xset", "-display", xdisplay, "q"],
                capture_output=True, text=True, timeout=3,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if "monitor is" in line.lower():
                        state = line.lower().split("monitor is")[-1].strip()
                        if state in ("standby", "suspend", "off"):
                            result = True
                        break
        except Exception:
            pass

    # Method 3: DRM connector status — all connectors disconnected/off
    if not result:
        try:
            import glob as _glob
            status_files = _glob.glob("/sys/class/drm/*/status")
            if status_files:
                statuses = []
                for sf in status_files:
                    try:
                        with open(sf) as f:
                            statuses.append(f.read().strip().lower())
                    except Exception:
                        pass
                if statuses and all(s == "disconnected" for s in statuses):
                    result = True
        except Exception:
            pass

    _display_asleep_cache = {"result": result, "ts": now}
    return result


# ---------------------------------------------------------------------------
# Window Session Tracker
# ---------------------------------------------------------------------------
class WindowTracker:
    def __init__(self, afk_timeout: float):
        self.afk_timeout = afk_timeout

        self.current_app = None
        self.current_title = None
        self.current_project = None
        self.session_start = None

        # Smart AFK: track when screen content last changed
        self.last_screen_change = datetime.now(timezone.utc)

        self.afk_state = "not-afk"
        self.afk_start = None
        self.active_start = datetime.now(timezone.utc)

        self.window_events = []
        self.afk_events = []

    def tick(self):
        now = datetime.now(timezone.utc)
        idle_secs = get_idle_seconds()

        info = get_active_window_info()
        if info is not None:
            new_app = info["app"]
            new_title = info["title"]

            # When an AI coding tool is running inside a terminal, override the
            # app/title so the activity is recorded as "Claude Code: ProjectName"
            # instead of "gnome-terminal" / "konsole".  Project is read from the
            # tool's /proc/<pid>/cwd — always the project root.
            if new_app.lower() in _TERMINAL_APP_NAMES:
                ai_tool, ai_project = _get_ai_tool_info()
                if ai_tool:
                    display = _AI_TOOL_DISPLAY.get(ai_tool, ai_tool.capitalize())
                    new_app = display
                    new_title = f"{display}: {ai_project}" if ai_project else display
                    info["app"] = new_app
                    info["title"] = new_title
                    if ai_project:
                        info["project"] = ai_project

            if new_app != self.current_app or new_title != self.current_title:
                # Only count as screen activity if user was recently active.
                # Prevents auto-updating titles (Gmail inbox count, browser refresh)
                # from blocking AFK detection when nobody is at the keyboard.
                if idle_secs < self.afk_timeout:
                    self.last_screen_change = now
                self._close_window_session(now)
                self.current_app = new_app
                self.current_title = new_title
                self.current_project = info.get("project")
                self.session_start = now

        self._update_afk(now, idle_secs)

    def _close_window_session(self, now):
        if self.current_app and self.session_start:
            duration = (now - self.session_start).total_seconds()
            if duration >= 5:
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

        Smart AFK rules (in priority order):
        1. Hard cap exceeded → always AFK.
           AI tool title: 30 min cap. All other apps: 2× afk_timeout (6 min).
        2. Claude Code process running → not AFK.
        3. AI tool / team chat window title active → not AFK (reading responses).
        4. Screen content changed recently → not AFK.
        5. Otherwise → AFK.
        """
        secs_since_screen_change = (now - self.last_screen_change).total_seconds()
        screen_active = secs_since_screen_change < self.afk_timeout

        if self.afk_state == "not-afk" and idle_secs >= self.afk_timeout:
            ai_title_active = is_ai_tool_or_chat_active(self.current_title)
            claude_code_running = is_claude_code_active()
            # Claude Code and AI tools both get the 30-min hard cap.
            # Without this, watching Claude run a long task (> 6 min) with no
            # keyboard input would wrongly mark the developer as AFK.
            hard_cap_secs = 1800 if (ai_title_active or claude_code_running) else self.afk_timeout * 2
            hard_cap_exceeded = idle_secs >= hard_cap_secs
            claude_active = not hard_cap_exceeded and claude_code_running
            ai_active = not hard_cap_exceeded and ai_title_active
            if not hard_cap_exceeded and (screen_active or claude_active or ai_active):
                return  # Still productive
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
        self.last_tick_time = time.time()
        self.idle_paused = False
        self.idle_pause_start_time: float | None = None
        self.deep_idle_mode = False

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
                # --- Sleep/hibernate detection ---
                # If wall-clock gap >> capture interval, the machine was suspended.
                # Close the open window session at the moment of sleep and record
                # an AFK event for the entire gap so the time isn't counted as work.
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
                        self.idle_pause_start_time = time.time()
                self.last_tick_time = now_wall

                idle_secs = get_idle_seconds()
                screen_locked = is_screen_locked()
                display_asleep = is_display_asleep()
                afk_timeout = self.config["afk_timeout_seconds"]
                screen_changing = (
                    (datetime.now(timezone.utc) - self.tracker.last_screen_change).total_seconds()
                    < afk_timeout
                )
                # AI tools and Claude Code get a 30-min hard cap; all other apps use 2× afk_timeout (6 min).
                # Watching Claude run a long task or reading AI responses easily takes 10-15 min
                # without keyboard input — the old 6-min cap would wrongly mark them AFK.
                # display_asleep gates everything: if the lid is closed / screen is off,
                # no AI tool or screen change can keep the session alive.
                ai_title_active = is_ai_tool_or_chat_active(self.tracker.current_title)
                claude_code_running = is_claude_code_active()
                hard_cap_secs = 1800 if (ai_title_active or claude_code_running) else afk_timeout * 2
                hard_cap_exceeded = idle_secs >= hard_cap_secs
                claude_active = not hard_cap_exceeded and not display_asleep and claude_code_running
                ai_active = not hard_cap_exceeded and not display_asleep and ai_title_active
                should_pause = screen_locked or display_asleep or hard_cap_exceeded or (
                    idle_secs >= afk_timeout and not screen_changing
                    and not claude_active and not ai_active
                )

                if not self.idle_paused:
                    if should_pause:
                        # System idle / screen locked / display off — stop capturing
                        now_dt = datetime.now(timezone.utc)
                        afk_started = now_dt - timedelta(seconds=idle_secs)
                        if screen_locked:
                            self.logger.info("Screen locked — pausing activity capture")
                        elif display_asleep:
                            self.logger.info("Display off (lid closed / display sleep) — pausing activity capture")
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
                        self.idle_pause_start_time = time.time()
                    else:
                        # System active — normal capture
                        self.tracker.tick()
                else:
                    # Currently paused — wait for user to return
                    if not should_pause:
                        # Guard against false resume: if idle_secs is low but display is still
                        # off (lid still closed), don't resume — kernel may briefly reset idle timer.
                        if is_display_asleep():
                            self.logger.debug(
                                "idle_secs low but display is off — likely kernel event, staying paused"
                            )
                        else:
                            # User is back — resume capture
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
                            self.idle_pause_start_time = None
                            self.logger.info("User activity detected — resuming capture")
                    else:
                        # Still idle — enter deep idle if idle >= shutdown_idle_seconds
                        shutdown_secs = self.config.get("shutdown_idle_seconds", 3600)
                        if (self.idle_pause_start_time is not None and
                                time.time() - self.idle_pause_start_time >= shutdown_secs):
                            self.logger.info(
                                f"Idle for {shutdown_secs // 60:.0f}+ min — "
                                "suspending agent; will resume automatically on user activity"
                            )
                            self.deep_idle_mode = True
                            # Flush + sync all pending data before going silent
                            self.tracker.flush_current()
                            w_ev, a_ev = self.tracker.drain_events()
                            self.sync_mgr.add_events(w_ev, a_ev)
                            if self.sync_mgr.pending_window or self.sync_mgr.pending_afk:
                                self.sync_mgr.sync()
                            # Minimal-poll loop: ~0% CPU while waiting for activity
                            while self.running:
                                time.sleep(30)
                                if get_idle_seconds() < self.config["afk_timeout_seconds"]:
                                    # Guard: don't wake if display is still off (lid still closed).
                                    if is_display_asleep():
                                        self.logger.debug(
                                            "Deep idle: idle_secs low but display is off "
                                            "— lid still closed, staying in deep idle"
                                        )
                                        continue
                                    self.logger.info(
                                        "User activity detected — waking agent from deep idle"
                                    )
                                    self.tracker = WindowTracker(
                                        afk_timeout=self.config["afk_timeout_seconds"]
                                    )
                                    self.idle_paused = False
                                    self.idle_pause_start_time = None
                                    self.deep_idle_mode = False
                                    self.last_sync = time.time()
                                    self.last_tick_time = time.time()
                                    break

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
    lock = check_single_instance()
    agent = ActivityAgent()
    agent.run()
