#!/usr/bin/env bash
# Build Anees for macOS
set -e

# ── Download static ffmpeg + ffprobe if not already present ───────────────────
# Binaries from https://evermeet.cx/ffmpeg/ (static macOS builds, no install needed)
VENDOR=vendor/macos
mkdir -p "$VENDOR"

download_if_missing() {
    local name="$1" url="$2"
    if [ ! -f "$VENDOR/$name" ]; then
        echo "Downloading $name…"
        curl -L "$url" -o "$VENDOR/${name}.7z"
        7z e "$VENDOR/${name}.7z" -o"$VENDOR" "$name" -y
        rm "$VENDOR/${name}.7z"
        chmod +x "$VENDOR/$name"
        echo "  → $VENDOR/$name"
    else
        echo "$name already present, skipping download."
    fi
}

# Static ARM64 builds (universal2 / arm64); update version numbers as needed
FFMPEG_URL="https://evermeet.cx/ffmpeg/ffmpeg-7.1.7z"
FFPROBE_URL="https://evermeet.cx/ffmpeg/ffprobe-7.1.7z"
download_if_missing ffmpeg  "$FFMPEG_URL"
download_if_missing ffprobe "$FFPROBE_URL"

# ── Build ─────────────────────────────────────────────────────────────────────
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
