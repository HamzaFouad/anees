from __future__ import annotations
import os
from typing import Callable
from backend.models import Playlist


def make_info_opts() -> dict:
    """Options for flat playlist metadata fetch (no download)."""
    return {
        "quiet":        True,
        "no_warnings":  True,
        "extract_flat": True,
    }


def make_download_opts(
    playlist: Playlist,
    output_dir: str,
    on_progress: Callable[[dict], None],
) -> dict:
    out_tmpl = os.path.join(
        output_dir,
        f"{playlist.prefix}_%(playlist_index)02d_%(title).60s.%(ext)s",
    )
    return {
        "format":          "bestaudio/best",
        "postprocessors":  [
            {
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": "0",
            },
        ],
        "postprocessor_args": {"ffmpegextractaudio": ["-ac", "1"]},  # mono
        "outtmpl":         out_tmpl,
        "ignoreerrors":    True,
        "quiet":           True,
        "no_warnings":     True,
        "progress_hooks":  [on_progress],
    }
