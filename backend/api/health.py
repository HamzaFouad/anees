"""Health API used by app bootstrap and UI status surfaces."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_ok() -> bool:
    """Return True when ffmpeg is executable in this runtime."""
    from backend.commands.ffmpeg import ffmpeg_ok as _ffmpeg_ok
    return _ffmpeg_ok()


def get_ffmpeg_version() -> str:
    """Return ffmpeg version string (or '?' on failure)."""
    from backend.commands.ffmpeg import _find_ffmpeg
    exe = _find_ffmpeg()
    try:
        result = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=3)
        line = result.stdout.split("\n")[0]
        return line.split("version ")[1].split(" ")[0] if "version" in line else "?"
    except Exception:
        return "?"


def get_ytdlp_version() -> str:
    """Return yt-dlp version string (or '?' on failure)."""
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return "?"


def get_disk_free_label() -> str:
    """Return a compact free-space label used by the status bar."""
    try:
        usage = shutil.disk_usage(str(Path.home() / "Downloads"))
        gb = usage.free / 1024 ** 3
        return f"{gb:.1f} GB free"
    except Exception:
        return ""
