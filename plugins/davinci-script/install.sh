#!/usr/bin/env bash
# EditClone — DaVinci Resolve Script Installer (macOS)
# Copies editclone_import.py to the DaVinci Resolve Scripts/Utility directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/editclone_import.py"
DEST_DIR="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"

echo "EditClone — DaVinci Resolve Script Installer"
echo "=============================================="

# Verify source file exists
if [ ! -f "$SRC" ]; then
  echo "ERROR: editclone_import.py not found at: $SRC"
  exit 1
fi

# Create destination directory if it doesn't exist
if [ ! -d "$DEST_DIR" ]; then
  echo "Creating directory: $DEST_DIR"
  mkdir -p "$DEST_DIR"
fi

# Copy the script
echo "Installing to: $DEST_DIR"
cp "$SRC" "$DEST_DIR/editclone_import.py"

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Open DaVinci Resolve"
echo "  2. Go to Workspace > Scripts > Utility > editclone_import"
echo "  3. On first run, enter your API URL and token when prompted"
echo ""
echo "API URL:   https://editclone-production.up.railway.app"
echo "Token:     Get from https://editclone.vercel.app/ja/account (API Keys section)"
