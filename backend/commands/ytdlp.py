from __future__ import annotations
import os
from pathlib import Path
from backend.models import Playlist


def _bin() -> str:
    vendor = Path(__file__).parent.parent.parent / "vendor" / "win-x64" / "yt-dlp.exe"
    if vendor.exists():
        return str(vendor)
    return "yt-dlp"


def _safe(s: str, maxlen: int = 40) -> str:
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in s)[:maxlen].strip("_ ")


def build_info_cmd(url: str, ytdlp_bin: str | None = None) -> list[str]:
    """Enumerate playlist entries without downloading."""
    return [
        ytdlp_bin or _bin(),
        "--flat-playlist",
        "--print", "%(title)s\t%(duration)s",
        "--no-warnings",
        url,
    ]


def build_download_cmd(
    playlist: Playlist,
    output_root: str,
    ytdlp_bin: str | None = None,
) -> list[str]:
    out_dir = os.path.join(output_root, f"{playlist.prefix}_{_safe(playlist.title)}")
    tmpl = os.path.join(out_dir, "%(playlist_index)02d_%(title).60s.%(ext)s")
    return [
        ytdlp_bin or _bin(),
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--postprocessor-args", "ffmpeg:-ac 1",
        "--output", tmpl,
        "--newline",
        "--no-warnings",
        "--ignore-errors",
        "--progress",
        playlist.url,
    ]
