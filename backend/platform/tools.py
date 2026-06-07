"""External tool discovery and health probes."""
from __future__ import annotations

import os
import subprocess
import sys

from backend.platform.resources import app_root, is_frozen


def ffmpeg_exe() -> str:
    if is_frozen():
        name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        bundled = str(app_root() / name)
        if os.path.exists(bundled):
            return bundled
    if sys.platform == "darwin":
        for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
            if os.path.exists(candidate):
                return candidate
    return "ffmpeg"


def ffprobe_exe() -> str:
    if is_frozen():
        name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
        bundled = str(app_root() / name)
        if os.path.exists(bundled):
            return bundled
    if sys.platform == "darwin":
        for candidate in ("/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"):
            if os.path.exists(candidate):
                return candidate
    return "ffprobe"


def ffmpeg_ok() -> bool:
    try:
        result = subprocess.run([ffmpeg_exe(), "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def ffprobe_ok() -> bool:
    try:
        result = subprocess.run([ffprobe_exe(), "-version"], capture_output=True, timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def ffmpeg_version() -> str:
    try:
        result = subprocess.run(
            [ffmpeg_exe(), "-version"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        line = result.stdout.split("\n")[0]
        return line.split("version ")[1].split(" ")[0] if "version" in line else "?"
    except Exception:
        return "?"
