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

# ── 1. Check binary exists ────────────────────────────────────────────────────
if [ ! -f "$AGENT_BIN" ]; then
    echo "ERROR: ActivityLedgerAgent binary not found in $AGENT_DIR"
    exit 1
fi
chmod +x "$AGENT_BIN"
echo "[1/4] Binary found and executable."

# ── 2. Install system dependencies ───────────────────────────────────────────
echo "[2/4] Checking system dependencies..."

MISSING=""
command -v xdotool    &>/dev/null || MISSING="$MISSING xdotool"
command -v xprintidle &>/dev/null || MISSING="$MISSING xprintidle"
command -v xprop      &>/dev/null || MISSING="$MISSING x11-utils"

if [ -n "$MISSING" ]; then
    echo "  Installing missing tools:$MISSING"
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y -qq xdotool xprintidle x11-utils
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y xdotool xprintidle xorg-x11-utils
    elif command -v pacman &>/dev/null; then
        sudo pacman -Sy --noconfirm xdotool xorg-xprop
    else
        echo "  WARNING: Could not auto-install. Please install manually: $MISSING"
    fi
else
    echo "  All dependencies already installed."
fi

# ── 3. Update config.json ─────────────────────────────────────────────────────
echo "[3/4] Updating config.json..."

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

# ── 4. Restart agent ──────────────────────────────────────────────────────────
echo "[4/4] Restarting agent..."

if command -v systemctl &>/dev/null && systemctl --user is-active activityledger.service &>/dev/null 2>&1; then
    systemctl --user restart activityledger.service
    sleep 2
    if systemctl --user is-active activityledger.service &>/dev/null; then
        echo "  Agent restarted via systemd ✓"
    else
        echo "  WARNING: systemd restart failed. Check: systemctl --user status activityledger"
    fi
else
    pkill -f "ActivityLedgerAgent" 2>/dev/null || true
    sleep 1
    nohup "$AGENT_BIN" > "$AGENT_DIR/agent_stdout.log" 2>"$AGENT_DIR/agent_stderr.log" &
    AGENT_PID=$!
    sleep 2
    if kill -0 $AGENT_PID 2>/dev/null; then
        echo "  Agent started (PID: $AGENT_PID) ✓"
    else
        echo "  WARNING: Agent may have failed to start. Check: $AGENT_DIR/agent_stderr.log"
    fi
fi

echo ""
echo "============================================"
echo "  Done! Data will sync every 5 minutes."
echo "  Logs: $AGENT_DIR/activity_agent.log"
echo "============================================"
