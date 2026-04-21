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
    "windows default lock screen", "lock screen", "new tab", "blank", "notification center", "loginwindow"])

def get_active_window_info():
    try:
        app_script = 'tell application "System Events" to get name of first application process whose frontmost is true'
        app_result = subprocess.run(["osascript", "-e", app_script], capture_output=True, text=True, timeout=5)
        if app_result.returncode != 0 or not app_result.stdout.strip(): return None
        app_name = app_result.stdout.strip()
        title_script = 'tell application "System Events" to get name of front window of (first application process whose frontmost is true)'
        title_result = subprocess.run(["osascript", "-e", title_script], capture_output=True, text=True, timeout=5)
        title = title_result.stdout.strip() if title_result.returncode == 0 else app_name
        if title.lower() in SKIP_TITLES: return None
        return {"app": app_name, "title": title}
    except: return None

def get_idle_seconds():
    try:
        result = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4", "-S"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0: return 0.0
        match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
        if match: return int(match.group(1)) / 1_000_000_000
        return 0.0
    except: return 0.0

class WindowTracker:
    def __init__(self, afk_timeout):
        self.afk_timeout = afk_timeout
        self.current_app = None; self.current_title = None; self.session_start = None
        self.afk_state = "not-afk"; self.afk_start = None; self.active_start = datetime.now(timezone.utc)
        self.window_events = []; self.afk_events = []

    def tick(self):
        now = datetime.now(timezone.utc); idle_secs = get_idle_seconds()
        self._update_afk(now, idle_secs)
        info = get_active_window_info()
        if info is None: return
        if info["app"] != self.current_app or info["title"] != self.current_title:
            self._close_window_session(now)
            self.current_app = info["app"]; self.current_title = info["title"]; self.session_start = now

    def _close_window_session(self, now):
        if self.current_app and self.session_start:
            duration = (now - self.session_start).total_seconds()
            if duration >= 5:
                self.window_events.append({"timestamp": self.session_start.isoformat(), "duration": round(duration, 1),
                    "data": {"app": self.current_app, "title": self.current_title or ""}})

    def _update_afk(self, now, idle_secs):
        if self.afk_state == "not-afk" and idle_secs >= self.afk_timeout:
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
        self.tracker = WindowTracker(afk_timeout=self.config["afk_timeout_seconds"])
        self.sync_mgr = SyncManager(self.config, self.logger)
        self.running = True; self.last_sync = time.time()
        signal.signal(signal.SIGTERM, self._shutdown); signal.signal(signal.SIGINT, self._shutdown)
        atexit.register(self._on_exit)

    def _shutdown(self, signum, frame): self.logger.info(f"Shutdown signal {signum}"); self.running = False
    def _on_exit(self):
        self.tracker.flush_current(); w, a = self.tracker.drain_events()
        self.sync_mgr.add_events(w, a); self.sync_mgr._save_queue(); self.logger.info("Saved pending events on exit")

    def run(self):
        self.logger.info("=" * 50); self.logger.info("Activity Agent started (macOS)")
        self.logger.info(f"Developer: {self.config['developer_id']}"); self.logger.info(f"Server: {self.config['server_url']}")
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

# Unload existing if present
if launchctl list 2>/dev/null | grep -q "com.activityledger.agent"; then
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
fi

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
