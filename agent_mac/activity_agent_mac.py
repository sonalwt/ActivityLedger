"""
Activity Ledger Agent - Lightweight activity tracker for macOS.

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
import re
import atexit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Paths & Config
# ---------------------------------------------------------------------------
# When bundled as binary by PyInstaller, sys.executable is the binary path.
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
    "shutdown_idle_seconds": 3600,
    "queue_file": str(AGENT_DIR / "pending_events.json"),
    "log_file": str(AGENT_DIR / "activity_agent.log"),
    "max_queue_size": 10000,
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found at {CONFIG_FILE}")
        print("Run install_mac.sh first or create config.json manually.")
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
# Single Instance Lock (File Lock - macOS)
# ---------------------------------------------------------------------------
_lock_file = None  # Must survive garbage collection


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
    return _lock_file  # Keep reference alive


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
# macOS — Active Window Info (AppleScript)
# ---------------------------------------------------------------------------
# Titles to ignore (system/lock screens)
SKIP_TITLES = frozenset([
    "", "program manager", "task switching", "task view",
    "windows default lock screen", "lock screen", "new tab", "blank",
    "notification center", "loginwindow", "missing value",
])

# Browser apps with AppleScript support for tab title + URL
BROWSER_SCRIPTS = {
    "Google Chrome": {
        "title": 'tell application "Google Chrome" to get title of active tab of front window',
        "url": 'tell application "Google Chrome" to get URL of active tab of front window',
    },
    "Google Chrome Canary": {
        "title": 'tell application "Google Chrome Canary" to get title of active tab of front window',
        "url": 'tell application "Google Chrome Canary" to get URL of active tab of front window',
    },
    "Safari": {
        "title": 'tell application "Safari" to get name of current tab of front window',
        "url": 'tell application "Safari" to get URL of current tab of front window',
    },
    "Brave Browser": {
        "title": 'tell application "Brave Browser" to get title of active tab of front window',
        "url": 'tell application "Brave Browser" to get URL of active tab of front window',
    },
    "Microsoft Edge": {
        "title": 'tell application "Microsoft Edge" to get title of active tab of front window',
        "url": 'tell application "Microsoft Edge" to get URL of active tab of front window',
    },
    "Vivaldi": {
        "title": 'tell application "Vivaldi" to get title of active tab of front window',
        "url": 'tell application "Vivaldi" to get URL of active tab of front window',
    },
    "Opera": {
        "title": 'tell application "Opera" to get title of active tab of front window',
        "url": 'tell application "Opera" to get URL of active tab of front window',
    },
    "Dia": {
        "title": 'tell application "Dia" to get title of active tab of front window',
        "url": 'tell application "Dia" to get URL of active tab of front window',
    },
}

# App names that are browsers (for URL capture and title formatting)
BROWSER_NAMES = frozenset(list(BROWSER_SCRIPTS.keys()) + [
    "Firefox", "Arc", "Orion", "Waterfox", "Chromium",
])


_log = logging.getLogger("activity_agent")


def _run_osascript(script, timeout=3):
    """Run an AppleScript (single-line) and return stdout, or None."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            val = result.stdout.strip()
            if val and val.lower() != "missing value":
                return val
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def _run_osascript_multi(*lines, timeout=5):
    """Run a multi-line AppleScript using separate -e flags (most reliable)."""
    try:
        cmd = ["osascript"]
        for line in lines:
            cmd.extend(["-e", line])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            val = result.stdout.strip()
            if val and val.lower() != "missing value":
                return val
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


# ---------------------------------------------------------------------------
# IDE Project Folder Detection (from process working directory)
# ---------------------------------------------------------------------------
IDE_APP_NAMES = {'visual studio code', 'code', 'cursor'}
_ide_project_cache = {}  # {app_lower: {"project": str, "time": float}}


# ---------------------------------------------------------------------------
# Cursor / VS Code — Active File from Local State Files
# (Fallback when AppleScript AXDocument fails for Electron apps)
# ---------------------------------------------------------------------------
# App name → Application Support subdirectory
_IDE_APP_SUPPORT_DIR = {
    'cursor': 'Cursor',
    'visual studio code': 'Code',
    'code': 'Code',
}

_cursor_state_cache: dict = {}  # {"filename": str|None, "workspace": str|None, "time": float}


def _get_ide_active_file_from_storage(app_lower: str):
    """Read Cursor/VS Code local state files to get (filename, workspace).

    Two sources (no AppleScript — works even when accessibility is blocked):
    1. storage.json  → last active workspace folder name
    2. state.vscdb   → most recently opened file (SQLite, read-only)

    Returns (filename_or_None, workspace_or_None).
    Cached per call for 10 seconds to avoid repeated disk I/O.
    """
    now = time.time()
    cached = _cursor_state_cache.get(app_lower)
    if cached and now - cached["time"] < 10:
        return cached["filename"], cached["workspace"]

    filename = None
    workspace = None

    app_dir = _IDE_APP_SUPPORT_DIR.get(app_lower)
    if not app_dir:
        return None, None

    base = Path.home() / "Library" / "Application Support" / app_dir

    # 1. Workspace folder from storage.json (electron window state)
    try:
        storage_path = base / "storage.json"
        if storage_path.exists():
            data = json.loads(storage_path.read_text(encoding="utf-8"))
            win_state = data.get("windowsState", {})
            last_win = win_state.get("lastActiveWindow", {})
            folder_uri = last_win.get("folderUri", "")
            if folder_uri.startswith("file://"):
                workspace = folder_uri.rstrip("/").rsplit("/", 1)[-1] or None
    except Exception:
        pass

    # 2. Most recently opened file from global SQLite state
    try:
        import sqlite3
        db_path = base / "User" / "globalStorage" / "state.vscdb"
        if db_path.exists():
            # immutable=1 prevents acquiring locks (safe while Cursor is running)
            conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
            try:
                row = conn.execute(
                    "SELECT value FROM ItemTable "
                    "WHERE key = 'history.recentlyOpenedPathsList'"
                ).fetchone()
                if row:
                    entries = json.loads(row[0]).get("entries", [])
                    for entry in entries:
                        file_uri = entry.get("fileUri", "")
                        if file_uri.startswith("file://"):
                            fn = file_uri.rstrip("/").rsplit("/", 1)[-1]
                            # Must look like a real source file (has extension)
                            if fn and "." in fn:
                                filename = fn
                                break
            finally:
                conn.close()
    except Exception:
        pass

    _cursor_state_cache[app_lower] = {"filename": filename, "workspace": workspace, "time": now}
    return filename, workspace


def _get_ide_project_folder(app_name):
    """Get project folder name from IDE process working directory. Cached for 5 min."""
    app_lower = (app_name or "").lower()
    if app_lower not in IDE_APP_NAMES:
        return None

    # Check cache (valid for 5 minutes)
    cached = _ide_project_cache.get(app_lower)
    if cached and time.time() - cached["time"] < 300:
        return cached["project"]

    try:
        # Get PID of the app
        pid_str = _run_osascript(
            f'tell application "System Events" to get unix id of '
            f'first application process whose displayed name is "{app_name}"',
            timeout=3,
        )
        if not pid_str:
            return None

        # Get working directory via lsof
        result = subprocess.run(
            ['lsof', '-p', pid_str, '-d', 'cwd', '-Fn'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('n') and line != 'n':
                    cwd = line[1:]  # Remove 'n' prefix
                    project = os.path.basename(cwd)
                    if project and project != '/':
                        _ide_project_cache[app_lower] = {"project": project, "time": time.time()}
                        return project

        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AppleScript — App name + Window title (multiple fallback strategies)
# ---------------------------------------------------------------------------
def get_active_window_info():
    """Return {"app": ..., "title": ..., "url": ...} or None.

    Tries multiple methods to capture window info reliably:
    1. Combined System Events script (displayed name + window title)
    2. Separate one-liner calls as fallback
    3. App-specific scripting for IDEs (Cursor, VS Code, etc.)
    4. Browser-specific scripting for tab title + URL
    """
    try:
        # === Step 1: Get app display name + window title (combined, reliable) ===
        combined = _run_osascript_multi(
            'tell application "System Events"',
            '  set fp to first application process whose frontmost is true',
            '  set appName to displayed name of fp',
            '  set windowTitle to ""',
            '  try',
            '    set windowTitle to name of front window of fp',
            '  end try',
            '  if windowTitle is "" or windowTitle is missing value then',
            '    try',
            '      set windowTitle to value of attribute "AXTitle" of front window of fp',
            '    end try',
            '  end if',
            '  return appName & "|||" & windowTitle',
            'end tell',
        )

        app_name = None
        title = None

        if combined and "|||" in combined:
            parts = combined.split("|||", 1)
            app_name = parts[0].strip()
            title = parts[1].strip() if len(parts) > 1 else ""
            if not title:
                title = None

        # === Step 2: Fallback — separate one-liner calls ===
        if not app_name:
            app_name = _run_osascript(
                'tell application "System Events" to get displayed name of '
                'first application process whose frontmost is true',
                timeout=5,
            )
        if not app_name:
            app_name = _run_osascript(
                'tell application "System Events" to get name of '
                'first application process whose frontmost is true',
                timeout=5,
            )
        if not app_name:
            return None

        if not title:
            title = _run_osascript(
                'tell application "System Events" to get name of front window '
                'of (first application process whose frontmost is true)',
                timeout=5,
            )
        if not title:
            title = _run_osascript(
                'tell application "System Events" to get value of attribute "AXTitle" '
                'of front window of (first application process whose frontmost is true)',
                timeout=5,
            )

        # === Step 3: App-specific scripting for IDEs (Electron apps) ===
        # System Events often can't read Electron window titles.
        # Try multiple strategies to get a meaningful title for Cursor / VS Code.
        if not title or title == app_name:
            app_lower = app_name.lower()
            if app_lower in ('cursor', 'visual studio code', 'code'):
                # Strategy A: AXDocument gives the file:// URL of the current file.
                # e.g. "file:///Users/vatsal/Data/src/index.tsx" → "index.tsx"
                ax_doc = _run_osascript_multi(
                    'tell application "System Events"',
                    f'  tell process "{app_name}"',
                    '    set docAttr to value of attribute "AXDocument" of front window',
                    '    return docAttr',
                    '  end tell',
                    'end tell',
                    timeout=4,
                )
                if ax_doc and ax_doc.startswith('file://'):
                    filename = ax_doc.rstrip('/').rsplit('/', 1)[-1]
                    if filename:
                        title = f"{filename} — {app_name}"

                # Strategy B: Iterate all windows to find one with a real title
                # (Cursor sometimes has a titled main window that AXTitle misses)
                if not title or title == app_name:
                    all_titles = _run_osascript_multi(
                        'tell application "System Events"',
                        f'  tell process "{app_name}"',
                        '    set result to ""',
                        '    repeat with w in every window',
                        '      set t to title of w',
                        '      if t is not "" and t is not missing value then',
                        f'        if t is not "{app_name}" then',
                        '          set result to t',
                        '          exit repeat',
                        '        end if',
                        '      end if',
                        '    end repeat',
                        '    return result',
                        '  end tell',
                        'end tell',
                        timeout=4,
                    )
                    if all_titles:
                        title = all_titles

                # Strategy C: Read Cursor/VS Code local state files (no AppleScript).
                # Works even when Accessibility is blocked or AXDocument returns nil.
                # Reads storage.json (workspace folder) and state.vscdb (recent file).
                if not title or title == app_name:
                    ide_file, ide_workspace = _get_ide_active_file_from_storage(app_lower)
                    if ide_file:
                        title = f"{ide_file} — {app_name}"
                    elif ide_workspace:
                        title = f"{ide_workspace} — {app_name}"

            # Strategy D: Generic — ask the app directly
            if not title or title == app_name:
                app_title = _run_osascript(
                    f'tell application "{app_name}" to get name of front window',
                    timeout=3,
                )
                if app_title:
                    title = app_title

        # === Step 4: Browser — get tab title + URL ===
        url = None
        if app_name in BROWSER_SCRIPTS:
            scripts = BROWSER_SCRIPTS[app_name]
            tab_title = _run_osascript(scripts["title"])
            tab_url = _run_osascript(scripts["url"])

            if tab_url:
                url = tab_url
            if tab_title:
                title = f"{tab_title} - {app_name}"
        elif app_name in BROWSER_NAMES and (not title or title == app_name):
            # Firefox/Arc etc. — use System Events title (already captured above)
            pass

        # === Step 5: Final handling ===
        if not title:
            title = app_name

        if title.lower() in SKIP_TITLES:
            return None

        _log.debug(f"Captured: app={app_name}, title={title}, url={url}")

        info = {"app": app_name, "title": title}
        if url:
            info["url"] = url
        # Add project folder from IDE process (if applicable)
        project = _get_ide_project_folder(app_name)
        if project:
            info["project"] = project
        return info

    except Exception as e:
        _log.debug(f"get_active_window_info error: {e}")
        return None


# ---------------------------------------------------------------------------
# macOS — Idle / AFK Detection (via ioreg)
# ---------------------------------------------------------------------------
def get_idle_seconds() -> float:
    """Return seconds since last keyboard/mouse input."""
    try:
        result = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem", "-d", "4", "-S"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return 0.0
        # Look for HIDIdleTime in the output
        match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
        if match:
            idle_ns = int(match.group(1))
            return idle_ns / 1_000_000_000  # nanoseconds to seconds
        return 0.0
    except subprocess.TimeoutExpired:
        return 0.0
    except Exception:
        return 0.0


def is_screen_locked() -> bool:
    """Check if Mac screen is locked, screensaver is active, or display is sleeping."""
    try:
        # Check if loginwindow or screensaver is the frontmost app
        app = _run_osascript(
            'tell application "System Events" to get name of first application '
            'process whose frontmost is true',
            timeout=3,
        )
        if app is None:
            return True  # Can't get frontmost app — likely locked/sleeping
        if app.lower() in ("loginwindow", "screensaverengine"):
            return True
    except Exception:
        pass
    return False


def is_claude_code_active() -> bool:
    """Return True if Claude Code CLI is running as a process.

    When Claude Code is actively working (editing files, running commands),
    the user is productively engaged even without keyboard/mouse input.
    Uses pgrep with an exact name match for the 'claude' binary.
    """
    try:
        result = subprocess.run(
            ["pgrep", "-x", "claude"],
            capture_output=True, text=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


# Domains considered productive even when keyboard/mouse is idle.
# Developer is reading AI responses or participating in team communication.
AI_TOOL_DOMAINS: frozenset = frozenset([
    # Claude
    "claude.ai",
    # ChatGPT / OpenAI
    "chatgpt.com",
    "chat.openai.com",
    # Google AI
    "gemini.google.com",
    "aistudio.google.com",
    # Google Chat & Meet (team communication)
    "chat.google.com",
    "meet.google.com",
    # Other AI assistants
    "perplexity.ai",
    "copilot.microsoft.com",
    "grok.com",
    "phind.com",
    "you.com",
    "blackbox.ai",
])


def is_ai_tool_or_chat_active(current_url: str | None) -> bool:
    """Return True if the active browser tab is an AI tool or team chat.

    Called during idle detection to keep the session as 'productive' when
    the developer is waiting for AI output (Claude, ChatGPT, Gemini) or
    communicating via Google Chat / Meet — even without keyboard input.

    Uses the URL last captured by the window tracker (refreshed every 30 s).
    Callers use a 30-min hard cap for AI URLs instead of the default 6-min cap.
    """
    if not current_url:
        return False
    url_lower = current_url.lower()
    return any(domain in url_lower for domain in AI_TOOL_DOMAINS)


# ---------------------------------------------------------------------------
# macOS — Accessibility Permission Check
# ---------------------------------------------------------------------------
def check_accessibility():
    """Warn if Accessibility permission is not granted (required for window tracking)."""
    try:
        test_script = (
            'tell application "System Events" to get name of '
            'first application process whose frontmost is true'
        )
        result = subprocess.run(
            ["osascript", "-e", test_script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "not allowed assistive access" in stderr or "1002" in stderr:
                print("=" * 55)
                print("  ERROR: Accessibility permission required!")
                print("")
                print("  Go to: System Settings > Privacy & Security")
                print("         > Accessibility")
                print("  and enable this application (Terminal or the agent binary).")
                print("=" * 55)
                sys.exit(1)
    except Exception:
        pass  # Non-fatal; proceed and let get_active_window_info handle failures


# ---------------------------------------------------------------------------
# Window Session Tracker
# ---------------------------------------------------------------------------
class WindowTracker:
    def __init__(self, afk_timeout: float):
        self.afk_timeout = afk_timeout

        # Current window session
        self.current_app = None
        self.current_title = None
        self.current_url = None
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
            new_url = info.get("url")

            # If window changed, close previous session and open a new one
            if new_app != self.current_app or new_title != self.current_title:
                self.last_screen_change = now  # Screen content changed
                self._close_window_session(now)
                self.current_app = new_app
                self.current_title = new_title
                self.current_url = new_url
                self.current_project = info.get("project")
                self.session_start = now
            else:
                # Update URL even if app/title didn't change (tab URL can change)
                self.current_url = new_url

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
                if self.current_url:
                    event_data["url"] = self.current_url
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
        1. Hard cap: physical idle > 2× timeout (6 min) → always AFK,
           even if Claude Code is running (prevents overnight sessions).
        2. Claude Code process running → not AFK (user delegated to AI).
        3. AI tool / Google Chat open in browser → not AFK (reading responses).
        4. Screen content changed recently → not AFK (user is monitoring).
        5. Otherwise → AFK.
        """
        # Check if screen is still active (title/app changed recently)
        secs_since_screen_change = (now - self.last_screen_change).total_seconds()
        screen_active = secs_since_screen_change < self.afk_timeout

        if self.afk_state == "not-afk" and idle_secs >= self.afk_timeout:
            # Hard cap: prevents overnight / lunch-break sessions from running forever.
            # AI tools get a 30-min cap — reading long AI responses easily takes 10+ min.
            # Default cap: 2× afk_timeout (6 min) for all other apps.
            ai_url_active = is_ai_tool_or_chat_active(self.current_url)
            hard_cap_secs = 1800 if ai_url_active else self.afk_timeout * 2
            hard_cap_exceeded = idle_secs >= hard_cap_secs
            claude_active = not hard_cap_exceeded and is_claude_code_active()
            ai_active = not hard_cap_exceeded and ai_url_active
            if not hard_cap_exceeded and (screen_active or claude_active or ai_active):
                return  # Still productive — AI tool/chat open, Claude Code running, or screen changing
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
            from urllib.request import Request, urlopen
            from urllib.error import URLError, HTTPError

            data = json.dumps(payload).encode("utf-8")
            req = Request(self.config["server_url"], data=data, headers=headers, method="POST")

            resp = urlopen(req, timeout=30)
            result = json.loads(resp.read().decode("utf-8"))
            self.logger.info(
                f"Synced: {result.get('processed', 0)} activities, "
                f"{result.get('duplicates_skipped', 0)} dupes skipped"
            )
            self.pending_window.clear()
            self.pending_afk.clear()
            self._save_queue()
            return True
        except HTTPError as e:
            self.logger.error(f"Server returned {e.code}: {e.read().decode()[:200]}")
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

        # Check accessibility permission before starting
        self.logger.info("Checking macOS Accessibility permission...")
        check_accessibility()

        self.tracker = WindowTracker(afk_timeout=self.config["afk_timeout_seconds"])
        self.sync_mgr = SyncManager(self.config, self.logger)
        self.running = True
        self.last_sync = time.time()
        self.idle_paused = False
        self.idle_pause_start_time: float | None = None  # Wall time when idle_paused became True
        self.deep_idle_mode = False

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

    def _log_startup_diagnostic(self):
        """Log what the agent can capture — auto-diagnostic on startup."""
        info = get_active_window_info()
        if info:
            self.logger.info(f"Startup capture test: app={info.get('app')}, "
                             f"title={info.get('title')}, url={info.get('url', 'N/A')}")
        else:
            self.logger.warning("Startup capture test: FAILED to get any window info")

    def run(self):
        self.logger.info("=" * 50)
        self.logger.info("Activity Agent started (macOS)")
        self.logger.info(f"Developer: {self.config['developer_id']}")
        self.logger.info(f"Server: {self.config['server_url']}")
        self.logger.info(
            f"Capture: {self.config['capture_interval_seconds']}s, "
            f"Sync: {self.config['sync_interval_seconds']}s, "
            f"AFK timeout: {self.config['afk_timeout_seconds']}s"
        )
        self._log_startup_diagnostic()
        last_tick_wall = time.time()

        while self.running:
            try:
                # ----------------------------------------------------------
                # Sleep / lid-close detection
                # When macOS sleeps, the process is suspended. On wake, we
                # resume here with a large wall-clock gap. Without this check,
                # the entire sleep duration gets billed to the last open window.
                # ----------------------------------------------------------
                now_wall = time.time()
                gap = now_wall - last_tick_wall
                sleep_threshold = self.config["capture_interval_seconds"] + 60  # e.g. 90 s

                if gap > sleep_threshold:
                    sleep_start_dt = datetime.fromtimestamp(last_tick_wall, tz=timezone.utc)
                    wake_dt = datetime.fromtimestamp(now_wall, tz=timezone.utc)
                    self.logger.info(
                        f"Sleep/wake detected: gap={gap:.0f}s "
                        f"({sleep_start_dt.strftime('%H:%M:%S')} → {wake_dt.strftime('%H:%M:%S')})"
                    )

                    # Close the current window session ending at sleep-start
                    # (not at wake time — that would inflate the activity duration)
                    if self.tracker.current_app and self.tracker.session_start:
                        sleep_duration = (sleep_start_dt - self.tracker.session_start).total_seconds()
                        if sleep_duration >= 5:
                            event_data = {
                                "app": self.tracker.current_app,
                                "title": self.tracker.current_title or "",
                            }
                            if self.tracker.current_url:
                                event_data["url"] = self.tracker.current_url
                            if self.tracker.current_project:
                                event_data["project"] = self.tracker.current_project
                            self.tracker.window_events.append({
                                "timestamp": self.tracker.session_start.isoformat(),
                                "duration": round(sleep_duration, 1),
                                "data": event_data,
                            })
                    # Re-open the session from wake time
                    self.tracker.session_start = wake_dt

                    # Emit not-afk for the active period before sleep
                    if self.tracker.afk_state == "not-afk" and self.tracker.active_start:
                        active_dur = (sleep_start_dt - self.tracker.active_start).total_seconds()
                        if active_dur >= 1:
                            self.tracker.afk_events.append({
                                "timestamp": self.tracker.active_start.isoformat(),
                                "duration": round(active_dur, 1),
                                "data": {"status": "not-afk"},
                            })

                    # Emit afk event spanning the entire sleep gap
                    self.tracker.afk_events.append({
                        "timestamp": sleep_start_dt.isoformat(),
                        "duration": round(gap, 1),
                        "data": {"status": "afk"},
                    })

                    # Reset state: coming out of sleep = afk until user input seen
                    self.tracker.afk_state = "afk"
                    self.tracker.afk_start = sleep_start_dt
                    self.tracker.active_start = wake_dt
                    self.tracker.last_screen_change = wake_dt
                    self.idle_paused = True  # Force re-evaluation on next tick
                    self.idle_pause_start_time = time.time()

                last_tick_wall = now_wall
                # ----------------------------------------------------------

                idle_secs = get_idle_seconds()
                screen_locked = is_screen_locked()
                afk_timeout = self.config["afk_timeout_seconds"]
                screen_changing = (
                    (datetime.now(timezone.utc) - self.tracker.last_screen_change).total_seconds()
                    < afk_timeout
                )
                # AI tools get a 30-min hard cap; all other apps use 2× afk_timeout (6 min).
                # Reading a long AI response easily takes 10-15 min without keyboard input.
                ai_url_active = is_ai_tool_or_chat_active(self.tracker.current_url)
                hard_cap_secs = 1800 if ai_url_active else afk_timeout * 2
                hard_cap_exceeded = idle_secs >= hard_cap_secs
                # Claude Code process running counts as productive — don't pause
                # (skip the checks if hard cap already exceeded to save overhead)
                claude_active = not hard_cap_exceeded and is_claude_code_active()
                ai_active = not hard_cap_exceeded and ai_url_active
                should_pause = screen_locked or hard_cap_exceeded or (
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
                        self.tracker.current_url = None
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
                        self.idle_pause_start_time = None
                        self.logger.info("User activity detected — resuming capture")
                    else:
                        # Still idle — enter deep idle if idle >= shutdown_idle_seconds.
                        # Deep idle: stops all heavy work (AppleScript, window capture).
                        # A 30-second poll loop waits for physical activity to resume.
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
                                    # Physical activity detected — wake up
                                    self.logger.info(
                                        "User activity detected — waking agent from deep idle"
                                    )
                                    # Reinitialize tracker with clean state
                                    self.tracker = WindowTracker(
                                        afk_timeout=self.config["afk_timeout_seconds"]
                                    )
                                    self.idle_paused = False
                                    self.idle_pause_start_time = None
                                    self.deep_idle_mode = False
                                    self.last_sync = time.time()
                                    last_tick_wall = time.time()  # Prevent false sleep-gap
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
