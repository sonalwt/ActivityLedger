#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Activity Ledger Agent - Mac Installer"
echo "============================================"
echo ""

AGENT_DIR="$HOME/ActivityLedgerAgent"
CONFIG_FILE="$AGENT_DIR/config.json"
AGENT_SCRIPT="$AGENT_DIR/activity_agent_mac.py"

# Create agent directory
mkdir -p "$AGENT_DIR"

# Check python3 is available (comes pre-installed on Mac)
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Run: xcode-select --install"
    exit 1
fi

# --- Hardcoded settings (no need to ask developer) ---
SECRET="TimesheetMaster2025258c362c"
SERVER="https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook"

# --- Only ask for name ---
echo ""
read -p "Enter your Full Name (e.g. John Doe): " DEV_NAME

# Generate developer_id from name
DEV_ID=$(echo "$DEV_NAME" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9 ]//g' | sed 's/  */ /g' | sed 's/ /_/g' | cut -c1-50)

if [ -z "$DEV_ID" ]; then
    echo "ERROR: Could not generate developer ID from name."
    exit 1
fi

echo ""
echo "  Developer Name: $DEV_NAME"
echo "  Developer ID:   $DEV_ID"
echo ""

# --- Register developer in the backend database ---
BASE_URL=$(echo "$SERVER" | sed 's|/api/v1/activitywatch/webhook||')
AW_TOKEN="AWToken_$(openssl rand -base64 32 | tr -d '/+=' | head -c 43)"

echo "Registering developer in the portal..."
REGISTER_URL="${BASE_URL}/api/register-developer"

REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$REGISTER_URL" \
    -H "Content-Type: application/json" \
    -d "{\"developer_name\": \"$DEV_NAME\", \"api_token\": \"$AW_TOKEN\"}" \
    2>/dev/null) || true

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  Developer registered successfully!"
elif [ "$HTTP_CODE" = "400" ]; then
    echo "  Developer already registered. Continuing..."
else
    echo "  WARNING: Could not register (HTTP $HTTP_CODE)."
    echo "  Register manually at: ${BASE_URL}/register-developer"
fi
echo ""

# --- Save config ---
cat > "$CONFIG_FILE" <<JSONEOF
{
    "developer_id": "$DEV_ID",
    "server_url": "$SERVER",
    "master_secret": "$SECRET",
    "capture_interval_seconds": 30,
    "sync_interval_seconds": 300,
    "afk_timeout_seconds": 180
}
JSONEOF
echo "Configuration saved."
echo ""

# --- Extract agent script ---
echo "Installing agent..."
cat > "$AGENT_SCRIPT" << 'PYEOF'
"""
Activity Ledger Agent - Lightweight activity tracker for macOS.
Captures foreground window activity and AFK status,
syncs to ActivityLedger backend via stateless webhook.
"""
import json, os, sys, time, signal, hashlib, base64, logging, socket, subprocess, fcntl, re, atexit
from datetime import datetime, timezone, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

if getattr(sys, "frozen", False):
    AGENT_DIR = Path(sys.executable).parent.resolve()
else:
    AGENT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = AGENT_DIR / "config.json"
DEFAULT_CONFIG = {
    "developer_id": "", "server_url": "https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook",
    "master_secret": "", "capture_interval_seconds": 30, "sync_interval_seconds": 300,
    "afk_timeout_seconds": 180, "queue_file": str(AGENT_DIR / "pending_events.json"),
    "log_file": str(AGENT_DIR / "activity_agent.log"), "max_queue_size": 10000,
}

def load_config():
    if not CONFIG_FILE.exists():
        print(f"ERROR: Config not found at {CONFIG_FILE}"); sys.exit(1)
    with open(CONFIG_FILE, "r") as f: cfg = json.load(f)
    merged = {**DEFAULT_CONFIG, **cfg}
    if not merged["developer_id"]: print("ERROR: developer_id empty"); sys.exit(1)
    if not merged["master_secret"]: print("ERROR: master_secret empty"); sys.exit(1)
    return merged

def setup_logging(config):
    logger = logging.getLogger("activity_agent"); logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(config["log_file"], maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler); return logger

_lock_file = None
def check_single_instance():
    global _lock_file
    lock_path = AGENT_DIR / ".agent.lock"
    try:
        _lock_file = open(lock_path, "w")
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(str(os.getpid())); _lock_file.flush()
    except (IOError, OSError):
        print("Another instance already running. Exiting."); sys.exit(0)
    return _lock_file

_cached_token = None; _cached_year = None
def generate_token(developer_id, master_secret):
    global _cached_token, _cached_year
    current_year = datetime.now().year
    if _cached_token and _cached_year == current_year: return _cached_token
    token_input = f"{developer_id}:{master_secret}:{current_year}"
    token_hash = hashlib.sha256(token_input.encode()).hexdigest()
    token_bytes = bytes.fromhex(token_hash[:48])
    _cached_token = base64.urlsafe_b64encode(token_bytes).decode().rstrip("=")
    _cached_year = current_year; return _cached_token

SKIP_TITLES = frozenset(["", "program manager", "task switching", "task view",
    "windows default lock screen", "lock screen", "new tab", "blank",
    "notification center", "loginwindow", "missing value"])

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
}

BROWSER_NAMES = frozenset(list(BROWSER_SCRIPTS.keys()) + [
    "Firefox", "Arc", "Orion", "Waterfox", "Chromium",
])

_log = logging.getLogger("activity_agent")

def _run_osascript(script, timeout=3):
    """Run a single-line AppleScript and return stdout, or None."""
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            val = result.stdout.strip()
            if val and val.lower() != "missing value": return val
    except (subprocess.TimeoutExpired, Exception): pass
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
            if val and val.lower() != "missing value": return val
    except (subprocess.TimeoutExpired, Exception): pass
    return None

def get_active_window_info():
    """Return {"app": ..., "title": ..., "url": ...} or None.
    Tries multiple methods to capture window info reliably:
    1. Combined System Events script (displayed name + window title)
    2. Separate one-liner calls as fallback
    3. App-specific scripting for IDEs (Cursor, VS Code, etc.)
    4. Browser-specific scripting for tab title + URL
    """
    try:
        # Step 1: Get app display name + window title (combined, reliable)
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
            if not title: title = None

        # Step 2: Fallback — separate one-liner calls
        if not app_name:
            app_name = _run_osascript(
                'tell application "System Events" to get displayed name of '
                'first application process whose frontmost is true', timeout=5)
        if not app_name:
            app_name = _run_osascript(
                'tell application "System Events" to get name of '
                'first application process whose frontmost is true', timeout=5)
        if not app_name:
            return None

        if not title:
            title = _run_osascript(
                'tell application "System Events" to get name of front window '
                'of (first application process whose frontmost is true)', timeout=5)
        if not title:
            title = _run_osascript(
                'tell application "System Events" to get value of attribute "AXTitle" '
                'of front window of (first application process whose frontmost is true)', timeout=5)

        # Step 3: App-specific scripting for IDEs (Electron apps)
        if not title or title == app_name:
            app_title = _run_osascript(
                f'tell application "{app_name}" to get name of front window', timeout=3)
            if app_title: title = app_title

        # Step 4: Browser — get tab title + URL
        url = None
        if app_name in BROWSER_SCRIPTS:
            scripts = BROWSER_SCRIPTS[app_name]
            tab_title = _run_osascript(scripts["title"])
            tab_url = _run_osascript(scripts["url"])
            if tab_url: url = tab_url
            if tab_title: title = f"{tab_title} - {app_name}"
        elif app_name in BROWSER_NAMES and (not title or title == app_name):
            pass  # Firefox/Arc etc. — use System Events title already captured

        # Step 5: Final handling
        if not title: title = app_name
        if title.lower() in SKIP_TITLES: return None

        _log.debug(f"Captured: app={app_name}, title={title}, url={url}")
        info = {"app": app_name, "title": title}
        if url: info["url"] = url
        return info
    except Exception as e:
        _log.debug(f"get_active_window_info error: {e}")
        return None

def get_idle_seconds():
    try:
        result = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4", "-S"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0: return 0.0
        match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
        if match: return int(match.group(1)) / 1_000_000_000
        return 0.0
    except: return 0.0

def check_accessibility():
    """Warn if Accessibility permission is not granted."""
    try:
        test_script = ('tell application "System Events" to get name of '
                       'first application process whose frontmost is true')
        result = subprocess.run(["osascript", "-e", test_script], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "not allowed assistive access" in stderr or "1002" in stderr:
                print("=" * 55)
                print("  ERROR: Accessibility permission required!")
                print("  Go to: System Settings > Privacy & Security")
                print("         > Accessibility")
                print("  and enable Terminal or the agent binary.")
                print("=" * 55)
                sys.exit(1)
    except Exception: pass

class WindowTracker:
    def __init__(self, afk_timeout):
        self.afk_timeout = afk_timeout
        self.current_app = None; self.current_title = None; self.current_url = None
        self.session_start = None
        self.last_screen_change = datetime.now(timezone.utc)  # Smart AFK: track screen changes
        self.afk_state = "not-afk"; self.afk_start = None; self.active_start = datetime.now(timezone.utc)
        self.window_events = []; self.afk_events = []

    def tick(self):
        now = datetime.now(timezone.utc); idle_secs = get_idle_seconds()
        info = get_active_window_info()
        if info is not None:
            new_app = info["app"]; new_title = info["title"]; new_url = info.get("url")
            if new_app != self.current_app or new_title != self.current_title:
                self.last_screen_change = now  # Screen content changed
                self._close_window_session(now)
                self.current_app = new_app; self.current_title = new_title
                self.current_url = new_url; self.session_start = now
            else:
                self.current_url = new_url
        self._update_afk(now, idle_secs)

    def _close_window_session(self, now):
        if self.current_app and self.session_start:
            duration = (now - self.session_start).total_seconds()
            if duration >= 5:
                event_data = {"app": self.current_app, "title": self.current_title or ""}
                if self.current_url: event_data["url"] = self.current_url
                self.window_events.append({"timestamp": self.session_start.isoformat(), "duration": round(duration, 1),
                    "data": event_data})

    def _update_afk(self, now, idle_secs):
        # Smart AFK: if screen content is changing (AI tool working), don't go AFK
        secs_since_screen_change = (now - self.last_screen_change).total_seconds()
        screen_active = secs_since_screen_change < self.afk_timeout
        if self.afk_state == "not-afk" and idle_secs >= self.afk_timeout:
            if screen_active: return  # Screen changing — user is monitoring
            afk_started = now - timedelta(seconds=idle_secs)
            if self.active_start:
                active_dur = (afk_started - self.active_start).total_seconds()
                if active_dur >= 1:
                    self.afk_events.append({"timestamp": self.active_start.isoformat(), "duration": round(active_dur, 1), "data": {"status": "not-afk"}})
            self.afk_state = "afk"; self.afk_start = afk_started
        elif self.afk_state == "afk" and idle_secs < self.afk_timeout:
            if self.afk_start:
                afk_dur = (now - self.afk_start).total_seconds()
                if afk_dur >= 1:
                    self.afk_events.append({"timestamp": self.afk_start.isoformat(), "duration": round(afk_dur, 1), "data": {"status": "afk"}})
            self.afk_state = "not-afk"; self.active_start = now

    def flush_current(self):
        now = datetime.now(timezone.utc); self._close_window_session(now); self.session_start = now
        if self.afk_state == "not-afk" and self.active_start:
            dur = (now - self.active_start).total_seconds()
            if dur >= 1:
                self.afk_events.append({"timestamp": self.active_start.isoformat(), "duration": round(dur, 1), "data": {"status": "not-afk"}})
            self.active_start = now

    def drain_events(self):
        w = self.window_events[:]; a = self.afk_events[:]
        self.window_events.clear(); self.afk_events.clear(); return w, a

class SyncManager:
    def __init__(self, config, logger):
        self.config = config; self.logger = logger; self.hostname = socket.gethostname()
        self.queue_file = Path(config["queue_file"]); self.max_queue = config.get("max_queue_size", 10000)
        self.pending_window = []; self.pending_afk = []; self._load_queue()

    def add_events(self, window_events, afk_events):
        self.pending_window.extend(window_events); self.pending_afk.extend(afk_events)
        total = len(self.pending_window) + len(self.pending_afk)
        if total > self.max_queue:
            excess = total - self.max_queue
            if len(self.pending_window) > excess: self.pending_window = self.pending_window[excess:]
            else: self.pending_window.clear(); self.pending_afk = self.pending_afk[excess:]

    def sync(self):
        if not self.pending_window and not self.pending_afk: return True
        payload = {}
        if self.pending_window: payload[f"aw-watcher-window_{self.hostname}"] = self.pending_window
        if self.pending_afk: payload[f"aw-watcher-afk_{self.hostname}"] = self.pending_afk
        token = generate_token(self.config["developer_id"], self.config["master_secret"])
        headers = {"Developer-ID": self.config["developer_id"], "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            data = json.dumps(payload).encode("utf-8")
            req = Request(self.config["server_url"], data=data, headers=headers, method="POST")
            resp = urlopen(req, timeout=30)
            result = json.loads(resp.read().decode("utf-8"))
            self.logger.info(f"Synced: {result.get('processed', 0)} activities, {result.get('duplicates_skipped', 0)} dupes skipped")
            self.pending_window.clear(); self.pending_afk.clear(); self._save_queue(); return True
        except HTTPError as e:
            self.logger.error(f"Server returned {e.code}: {e.read().decode()[:200]}"); self._save_queue(); return False
        except Exception as e:
            self.logger.error(f"Sync failed (will retry): {e}"); self._save_queue(); return False

    def _save_queue(self):
        try: self.queue_file.write_text(json.dumps({"window": self.pending_window, "afk": self.pending_afk}), encoding="utf-8")
        except Exception as e: self.logger.error(f"Failed to save queue: {e}")

    def _load_queue(self):
        if self.queue_file.exists():
            try:
                data = json.loads(self.queue_file.read_text(encoding="utf-8"))
                self.pending_window = data.get("window", []); self.pending_afk = data.get("afk", [])
            except: pass

class ActivityAgent:
    def __init__(self):
        self.config = load_config(); self.logger = setup_logging(self.config)
        self.logger.info("Checking macOS Accessibility permission...")
        check_accessibility()
        self.tracker = WindowTracker(afk_timeout=self.config["afk_timeout_seconds"])
        self.sync_mgr = SyncManager(self.config, self.logger)
        self.running = True; self.last_sync = time.time()
        signal.signal(signal.SIGTERM, self._shutdown); signal.signal(signal.SIGINT, self._shutdown)
        atexit.register(self._on_exit)

    def _shutdown(self, signum, frame): self.logger.info(f"Shutdown signal {signum}"); self.running = False
    def _on_exit(self):
        self.tracker.flush_current(); w, a = self.tracker.drain_events()
        self.sync_mgr.add_events(w, a); self.sync_mgr._save_queue(); self.logger.info("Saved pending events on exit")

    def _log_startup_diagnostic(self):
        """Log what the agent can capture on startup."""
        info = get_active_window_info()
        if info:
            self.logger.info(f"Startup capture test: app={info.get('app')}, title={info.get('title')}, url={info.get('url', 'N/A')}")
        else:
            self.logger.warning("Startup capture test: FAILED to get any window info")

    def run(self):
        self.logger.info("=" * 50); self.logger.info("Activity Agent started (macOS)")
        self.logger.info(f"Developer: {self.config['developer_id']}"); self.logger.info(f"Server: {self.config['server_url']}")
        self._log_startup_diagnostic()
        while self.running:
            try:
                self.tracker.tick()
                now = time.time()
                if now - self.last_sync >= self.config["sync_interval_seconds"]:
                    self.tracker.flush_current(); w, a = self.tracker.drain_events()
                    self.sync_mgr.add_events(w, a); self.sync_mgr.sync(); self.last_sync = now
                time.sleep(self.config["capture_interval_seconds"])
            except Exception as e: self.logger.error(f"Main loop error: {e}", exc_info=True); time.sleep(5)
        self.logger.info("Activity Agent stopped")

if __name__ == "__main__":
    lock = check_single_instance(); agent = ActivityAgent(); agent.run()
PYEOF

# --- Setup LaunchAgent for auto-start ---
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.activityledger.agent.plist"
PYTHON_PATH="$(command -v python3)"
mkdir -p "$PLIST_DIR"

# Stop any existing agent — always try unload + kill
launchctl unload "$PLIST_FILE" 2>/dev/null || true
pkill -f "activity_agent_mac.py" 2>/dev/null || true
sleep 1

cat > "$PLIST_FILE" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.activityledger.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_PATH</string>
        <string>$AGENT_SCRIPT</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$AGENT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$AGENT_DIR/agent_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$AGENT_DIR/agent_stderr.log</string>
</dict>
</plist>
PLISTEOF

# Load and start
launchctl load "$PLIST_FILE"

echo ""
echo "============================================"
echo "  DONE! Agent installed and running."
echo ""
echo "  Developer '$DEV_NAME' registered in portal."
echo "  Activity capturing started."
echo "  Auto-starts on every login."
echo ""
echo "  IMPORTANT: Grant Accessibility permission:"
echo "    System Settings > Privacy & Security >"
echo "    Accessibility > Enable Terminal"
echo ""
echo "  Logs: $AGENT_DIR/activity_agent.log"
echo "============================================"
