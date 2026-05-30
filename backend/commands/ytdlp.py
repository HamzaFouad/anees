from __future__ import annotations
import os
import threading
from typing import Callable

from backend.models import Video


class YtdlpClient:
    """Single interface for all yt-dlp operations.

    Only this file imports yt_dlp — everything else goes through this class.
    """

    # ── Metadata ──────────────────────────────────────────────────────────────
    def fetch_info(self, url: str) -> tuple[list[Video], str]:
        """Fetch full playlist metadata including duration (no download).

        Does NOT use extract_flat so that duration is available for all
        video types (including Shorts). The YouTube browse API returns
        duration for all entries in the same round-trip, so this is still
        a single network request for most playlists.

        Returns (videos, playlist_title).
        """
        import yt_dlp
        videos: list[Video] = []
        title = ""
        opts = {
            "quiet":       True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get("title") or ""
                for entry in (info.get("entries") or []):
                    if entry:
                        videos.append(Video(
                            title        = entry.get("title") or f"Video {len(videos)+1}",
                            duration_sec = int(entry.get("duration") or 0),
                            stage        = "queued",
                        ))
        except Exception as exc:
            raise RuntimeError(f"fetch_info failed: {exc}") from exc
        return videos, title

    # ── Download ──────────────────────────────────────────────────────────────
    def download(
        self,
        url: str,
        output_template: str,
        on_progress:      Callable[[dict], None],
        on_postprocess:   Callable[[dict], None],
        stop:             threading.Event,
        pause:            threading.Event,
    ) -> None:
        """Download *url* using the given output template.

        Calls *on_progress* for each yt-dlp progress event and
        *on_postprocess* for each postprocessor completion.
        Respects *stop* (terminates) and *pause* (blocks) threading events.
        """
        import yt_dlp

        def _progress(d: dict) -> None:
            pause.wait()
            if stop.is_set():
                raise yt_dlp.utils.DownloadCancelled("stopped by user")
            on_progress(d)

        opts = {
            "format":          "bestaudio/best",
            "postprocessors":  [
                {
                    "key":              "FFmpegExtractAudio",
                    "preferredcodec":   "mp3",
                    "preferredquality": "0",
                },
            ],
            "postprocessor_args":  {"ffmpegextractaudio": ["-ac", "1"]},
            "outtmpl":             output_template,
            "ignoreerrors":        True,
            "quiet":               True,
            "no_warnings":         True,
            "progress_hooks":      [_progress],
            "postprocessor_hooks": [on_postprocess],
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadCancelled:
            pass   # normal stop — caller already set stop flag
