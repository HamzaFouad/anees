#!/usr/bin/env bash
# Build Anees for macOS
set -e
echo "Building Anees for macOS…"
.venv/bin/pyinstaller anees.spec --clean --noconfirm
echo "Done → dist/Anees.app"
