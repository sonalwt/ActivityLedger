#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Activity Ledger Agent - Mac Uninstaller"
echo "============================================"
echo ""

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.activityledger.agent.plist"

# Stop and unload the LaunchAgent
if [ -f "$PLIST_FILE" ]; then
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    rm -f "$PLIST_FILE"
    echo "  LaunchAgent stopped and removed."
else
    echo "  No LaunchAgent found."
fi

# Remove lock file
rm -f "$AGENT_DIR/.agent.lock"
echo "  Lock file removed."

echo ""
echo "============================================"
echo "  Uninstall complete."
echo ""
echo "  Config, logs, and queue files left in place."
echo "  To fully remove everything:"
echo "    rm -rf $AGENT_DIR"
echo "============================================"
