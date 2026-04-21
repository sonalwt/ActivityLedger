#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Activity Ledger Agent - Linux Uninstaller"
echo "============================================"
echo ""

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Stop systemd service if exists
if command -v systemctl &>/dev/null; then
    systemctl --user stop activityledger.service 2>/dev/null || true
    systemctl --user disable activityledger.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/activityledger.service"
    systemctl --user daemon-reload 2>/dev/null || true
    echo "  Systemd service removed."
fi

# Remove XDG autostart if exists
rm -f "$HOME/.config/autostart/activityledger.desktop"
echo "  Autostart entry removed."

# Remove lock file
rm -f "$AGENT_DIR/.agent.lock"
echo "  Lock file removed."

# Kill any running agent process
pkill -f "ActivityLedgerAgent" 2>/dev/null || true
echo "  Agent process stopped."

echo ""
echo "============================================"
echo "  Uninstall complete."
echo ""
echo "  Config and logs left in place."
echo "  To fully remove: rm -rf $AGENT_DIR"
echo "============================================"
