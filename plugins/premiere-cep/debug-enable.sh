#!/usr/bin/env bash
# EditClone — Premiere Pro CEP Debug Mode Enabler (macOS)
# Allows Premiere Pro to load unsigned (locally installed) CEP extensions.
#
# Run this once before installing the CEP panel.
# Safe to run multiple times.

set -euo pipefail

echo "EditClone — Enable CEP Debug Mode (macOS)"
echo "==========================================="
echo ""
echo "Setting PlayerDebugMode = 1 for CSXS 9-12..."
echo "(covers Premiere Pro CC 2019 through Premiere Pro 2025)"
echo ""

for VER in 9 10 11 12; do
  defaults write "com.adobe.CSXS.$VER" PlayerDebugMode 1
  echo "  com.adobe.CSXS.$VER  PlayerDebugMode = 1"
done

echo ""
echo "Done. Debug mode is now enabled."
echo ""
echo "Verify with:"
echo "  defaults read com.adobe.CSXS.11 PlayerDebugMode"
echo ""
echo "To disable debug mode later (re-enable signature enforcement):"
echo "  for VER in 9 10 11 12; do defaults delete \"com.adobe.CSXS.\$VER\" PlayerDebugMode; done"
