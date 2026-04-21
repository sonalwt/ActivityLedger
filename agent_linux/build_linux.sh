#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Building Activity Agent (Linux)"
echo "============================================"
echo ""

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    exit 1
fi

echo "Python: $(python3 --version)"
echo ""

echo "Installing dependencies..."
pip3 install requests pyinstaller
echo "Done."
echo ""

echo "Building standalone binary..."
pyinstaller \
    --onefile \
    --noconsole \
    --name "ActivityLedgerAgent" \
    --distpath "$AGENT_DIR/dist" \
    --workpath "$AGENT_DIR/build" \
    --specpath "$AGENT_DIR" \
    "$AGENT_DIR/activity_agent_linux.py"

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "  BUILD SUCCESSFUL!"
    echo ""
    echo "  Binary: $AGENT_DIR/dist/ActivityLedgerAgent"
    echo ""
    echo "  To deploy:"
    echo "  1. Copy dist/ActivityLedgerAgent to the machine"
    echo "  2. Copy install_linux.sh to the same folder"
    echo "  3. Run: bash install_linux.sh"
    echo "============================================"
else
    echo "BUILD FAILED."
    exit 1
fi
