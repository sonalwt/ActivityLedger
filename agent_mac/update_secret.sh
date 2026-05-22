#!/bin/bash
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$AGENT_DIR/config.json"
AGENT_BIN="$AGENT_DIR/ActivityLedgerAgent"

MASTER_SECRET="TimesheetMaster2025258c362c"
SERVER_URL="https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook"

echo "============================================"
echo "  ActivityLedger Agent - Setup & Sync Fix"
echo "============================================"
echo ""

# ── 1. Check binary ───────────────────────────────────────────────────────────
if [ ! -f "$AGENT_BIN" ]; then
    echo "ERROR: ActivityLedgerAgent binary not found in $AGENT_DIR"
    exit 1
fi
chmod +x "$AGENT_BIN"
echo "[1/3] Binary found and executable."

# ── 2. Update config.json ─────────────────────────────────────────────────────
echo "[2/3] Updating config.json..."

if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: config.json not found at $CONFIG_FILE"
    exit 1
fi

python3 - <<PYEOF
import json

with open("$CONFIG_FILE", "r") as f:
    config = json.load(f)

config["master_secret"] = "$MASTER_SECRET"
config["server_url"] = "$SERVER_URL"

with open("$CONFIG_FILE", "w") as f:
    json.dump(config, f, indent=4)

print("  master_secret -> updated")
print("  server_url    -> updated")
print("  developer_id  ->", config.get("developer_id", "NOT SET"))
PYEOF

# ── 3. Restart agent ──────────────────────────────────────────────────────────
echo "[3/3] Restarting agent..."

pkill -f "ActivityLedgerAgent" 2>/dev/null || true
sleep 1

# Check for LaunchAgent plist
PLIST="$HOME/Library/LaunchAgents/com.activityledger.agent.plist"
if [ -f "$PLIST" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST"
    echo "  Agent restarted via LaunchAgent ✓"
else
    nohup "$AGENT_BIN" > "$AGENT_DIR/agent_stdout.log" 2>"$AGENT_DIR/agent_stderr.log" &
    AGENT_PID=$!
    sleep 2
    if kill -0 $AGENT_PID 2>/dev/null; then
        echo "  Agent started (PID: $AGENT_PID) ✓"
    else
        echo "  WARNING: Agent may have failed. Check: $AGENT_DIR/agent_stderr.log"
    fi
fi

echo ""
echo "============================================"
echo "  Done! Data will sync every 5 minutes."
echo "  Logs: $AGENT_DIR/activity_agent.log"
echo "============================================"
