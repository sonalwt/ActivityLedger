#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  Building Activity Agent (macOS)"
echo "============================================"
echo ""

AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.8+ first."
    exit 1
fi

echo "Python: $(python3 --version)"
echo ""

# Install build dependencies
echo "Installing dependencies..."
pip3 install -r "$AGENT_DIR/requirements_mac.txt"
echo "Done."
echo ""

# Build single-file binary with PyInstaller
echo "Building standalone binary (this may take a minute)..."
pyinstaller \
    --onefile \
    --noconsole \
    --name "ActivityLedgerAgent" \
    --distpath "$AGENT_DIR/dist" \
    --workpath "$AGENT_DIR/build" \
    --specpath "$AGENT_DIR" \
    "$AGENT_DIR/activity_agent_mac.py"

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================"
    echo "  BUILD SUCCESSFUL!"
    echo ""
    echo "  Binary: $AGENT_DIR/dist/ActivityLedgerAgent"
    echo ""
    echo "  To deploy to a developer's Mac:"
    echo "  1. Copy dist/ActivityLedgerAgent to their Mac"
    echo "  2. Copy install_mac.sh to the same folder"
    echo "  3. Run: bash install_mac.sh"
    echo "============================================"
else
    echo ""
    echo "BUILD FAILED. Check errors above."
    exit 1
fi
