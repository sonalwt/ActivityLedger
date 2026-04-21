#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Activity Ledger Agent - Linux Installer"
echo "============================================"
echo ""

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$AGENT_DIR/config.json"
AGENT_BIN="$AGENT_DIR/ActivityLedgerAgent"

# Check that the binary exists
if [ ! -f "$AGENT_BIN" ]; then
    echo "ERROR: ActivityLedgerAgent binary not found in $AGENT_DIR"
    echo "Make sure the binary is in the same folder as this script."
    exit 1
fi

# Make binary executable
chmod +x "$AGENT_BIN"

# Create/update config if developer_id is empty or missing
NEED_CONFIG=false
if [ ! -f "$CONFIG_FILE" ]; then
    NEED_CONFIG=true
elif grep -q '"developer_id": ""' "$CONFIG_FILE" 2>/dev/null; then
    NEED_CONFIG=true
fi

if [ "$NEED_CONFIG" = true ]; then
    echo "--- Configuration ---"
    echo ""
    read -p "Enter Developer's Full Name (e.g. John Doe): " DEV_NAME
    read -p "Enter Master Secret: " SECRET
    read -p "Enter Server URL (press Enter for default): " SERVER
    SERVER=${SERVER:-"https://api-timesheet.firsteconomy.com/api/v1/activitywatch/webhook"}

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
    RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "200" ]; then
        echo "  Developer registered successfully!"
    elif [ "$HTTP_CODE" = "400" ]; then
        echo "  Note: Developer may already be registered."
        echo "  Continuing with agent setup..."
    else
        echo "  WARNING: Could not register (HTTP $HTTP_CODE)."
        echo "  You can register manually at: ${BASE_URL}/register-developer"
        echo "  Continuing with agent setup..."
    fi
    echo ""

    # Save config
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
fi

# --- Auto-start setup ---
# Method 1: systemd user service (preferred)
SYSTEMD_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SYSTEMD_DIR/activityledger.service"

if command -v systemctl &>/dev/null; then
    mkdir -p "$SYSTEMD_DIR"

    # Stop existing service if running
    systemctl --user stop activityledger.service 2>/dev/null || true
    systemctl --user disable activityledger.service 2>/dev/null || true

    cat > "$SERVICE_FILE" <<SVCEOF
[Unit]
Description=Activity Ledger Agent
After=graphical-session.target

[Service]
ExecStart=$AGENT_BIN
WorkingDirectory=$AGENT_DIR
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
SVCEOF

    systemctl --user daemon-reload
    systemctl --user enable activityledger.service
    systemctl --user start activityledger.service

    echo "Installed as systemd user service."
    echo ""
    echo "============================================"
    echo "  Installation complete!"
    echo ""
    echo "  Agent is running and will auto-start on login."
    echo ""
    echo "  Commands:"
    echo "    Status: systemctl --user status activityledger"
    echo "    Stop:   systemctl --user stop activityledger"
    echo "    Start:  systemctl --user start activityledger"
    echo "    Logs:   $AGENT_DIR/activity_agent.log"
    echo "============================================"
else
    # Method 2: XDG autostart (fallback for non-systemd systems)
    AUTOSTART_DIR="$HOME/.config/autostart"
    DESKTOP_FILE="$AUTOSTART_DIR/activityledger.desktop"
    mkdir -p "$AUTOSTART_DIR"

    cat > "$DESKTOP_FILE" <<DTEOF
[Desktop Entry]
Type=Application
Name=Activity Ledger Agent
Exec=$AGENT_BIN
Path=$AGENT_DIR
Hidden=false
X-GNOME-Autostart-enabled=true
Comment=Activity tracking agent
DTEOF

    # Start agent now
    nohup "$AGENT_BIN" > "$AGENT_DIR/agent_stdout.log" 2> "$AGENT_DIR/agent_stderr.log" &
    echo "Agent started (PID: $!)"

    echo ""
    echo "============================================"
    echo "  Installation complete!"
    echo ""
    echo "  Agent is running and will auto-start on login."
    echo ""
    echo "  To stop: kill $!"
    echo "  Logs:    $AGENT_DIR/activity_agent.log"
    echo "============================================"
fi
