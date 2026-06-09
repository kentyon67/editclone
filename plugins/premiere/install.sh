#!/usr/bin/env bash
# EditClone — Premiere Pro UXP Plugin Installer (macOS)
# Copies the UXP plugin to the correct directory and opens UXP Developer Tools.
#
# Requirements:
#   - Premiere Pro 2022 (v22.0) or later  (first version with UXP panel support)
#   - UXP Developer Tools app (free, download from Adobe Exchange)
#     https://exchange.adobe.com/apps/cc/106532/uxp-developer-tools

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="com.editclone.premiere-panel"

# UXP plugin directory (user-level, no admin required)
DEST_DIR="$HOME/Library/Application Support/Adobe/UXP/PluginsStorage/PPRO/11/Developer/$PLUGIN_ID/PluginData"

echo "EditClone — Premiere Pro UXP Plugin Installer"
echo "================================================"

# ---- 1. Create directory ----
echo ""
echo "[1/3] Creating plugin directory..."
if [ -d "$DEST_DIR" ]; then
  echo "      Removing existing installation: $DEST_DIR"
  rm -rf "$DEST_DIR"
fi
mkdir -p "$DEST_DIR"

# ---- 2. Copy plugin files ----
echo ""
echo "[2/3] Copying plugin files to: $DEST_DIR"
cp -r "$SCRIPT_DIR/." "$DEST_DIR/"
# Remove installer from installed copy
rm -f "$DEST_DIR/install.sh"

echo ""
echo "[3/3] Done."
echo ""
echo "================================================================"
echo "  IMPORTANT: UXP plugins must be loaded via UXP Developer Tools"
echo "================================================================"
echo ""
echo "Step 1. Download UXP Developer Tools (free):"
echo "  https://exchange.adobe.com/apps/cc/106532/uxp-developer-tools"
echo ""
echo "Step 2. Open UXP Developer Tools."
echo ""
echo "Step 3. Click 'Add Plugin' and select the manifest.json at:"
echo "  $SCRIPT_DIR/manifest.json"
echo ""
echo "Step 4. Click 'Load' next to the EditClone entry."
echo "        The panel will appear under Window > Extensions (Legacy) > EditClone"
echo "        in Premiere Pro."
echo ""
echo "Step 5. For persistent loading across Premiere restarts:"
echo "  - In UXP Developer Tools, click the ... menu beside EditClone"
echo "  - Choose 'Auto-load on launch'"
echo ""
echo "Plugin directory: $DEST_DIR"
echo "API URL:          https://editclone-production.up.railway.app"
echo "Web app:          https://editclone.vercel.app"
