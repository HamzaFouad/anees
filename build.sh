#!/usr/bin/env bash
# Build Anees for macOS
set -e
echo "Building Anees for macOS…"
.venv/bin/pyinstaller anees.spec --clean --noconfirm

# Ad-hoc code sign — removes Gatekeeper prompt for locally-built apps.
# For public distribution replace '-' with a Developer ID certificate:
#   codesign --force --deep --sign "Developer ID Application: Your Name (TEAMID)"
echo "Signing Anees.app (ad-hoc)…"
codesign --force --deep --sign - dist/Anees.app

echo "Done → dist/Anees.app"
echo ""
echo "NOTE: if Gatekeeper still blocks a downloaded build, strip quarantine:"
echo "  xattr -dr com.apple.quarantine dist/Anees.app"
