#!/usr/bin/env bash
# EditClone — Premiere Pro CEP Extension Installer (macOS)
# Copies the CEP panel to Adobe's extension directory.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXTENSION_ID="com.editclone.premiere"
DEST_DIR="$HOME/Library/Application Support/Adobe/CEP/extensions/$EXTENSION_ID"

echo "EditClone — Premiere Pro CEP Installer"
echo "======================================="

# ---- 1. Enable unsigned extension loading (debug mode) ----
echo ""
echo "[1/3] Enabling unsigned extension loading..."
PLIST_KEY="PlayerDebugMode"

# Try CSXS versions 9 through 12 (covers Premiere CC 2022–2025)
for VER in 9 10 11 12; do
  defaults write "com.adobe.CSXS.$VER" "$PLIST_KEY" 1 2>/dev/null && \
    echo "      Set com.adobe.CSXS.$VER PlayerDebugMode = 1"
done

echo "      Done."

# ---- 2. Create destination directory ----
echo ""
echo "[2/3] Creating extension directory..."
if [ -d "$DEST_DIR" ]; then
  echo "      Removing existing installation: $DEST_DIR"
  rm -rf "$DEST_DIR"
fi
mkdir -p "$DEST_DIR"

# ---- 3. Copy extension files ----
echo ""
echo "[3/3] Copying extension files to: $DEST_DIR"
cp -r "$SCRIPT_DIR/." "$DEST_DIR/"

# Remove installer scripts from the installed copy (not needed inside Premiere)
rm -f "$DEST_DIR/install.sh" "$DEST_DIR/install.bat"
rm -f "$DEST_DIR/debug-enable.sh" "$DEST_DIR/debug-enable.bat"

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Quit Premiere Pro if it is running"
echo "  2. Re-open Premiere Pro"
echo "  3. Go to Window > Extensions > EditClone"
echo ""
echo "  If the panel does not appear:"
echo "    - Confirm Premiere Pro version is CC 2019 (v13.0) or later"
echo "    - Verify debug mode with: defaults read com.adobe.CSXS.11 PlayerDebugMode"
echo "    - Check extension directory: ls \"$DEST_DIR\""
echo ""
echo "API URL:   https://editclone-production.up.railway.app"
echo "Web app:   https://editclone.vercel.app"
