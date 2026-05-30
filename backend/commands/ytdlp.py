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
        """Fetch playlist metadata in a single network request (no download).

        Uses extract_flat so the playlist page is fetched once rather than
        making a separate request per video. Duration is populated for
        regular YouTube videos from the playlist API response (lengthText).
        YouTube Shorts omit lengthText in the playlist API, so their
        duration stays 0 and is filled in later via on_video_meta when
        each Short finishes downloading.

        Returns (videos, playlist_title).
        """
        import yt_dlp
        videos: list[Video] = []
        title = ""
        opts = {
            "quiet":        True,
            "no_warnings":  True,
            "extract_flat": True,
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
            # bestaudio picks the highest-quality stream available; if the
            # source is below 192 kbps the CBR target is simply unreachable
            # and ffmpeg encodes at whatever the source provides.
            "format":          "bestaudio/best",
            "postprocessors":  [
                {
                    "key":              "FFmpegExtractAudio",
                    "preferredcodec":   "mp3",
                    "preferredquality": "192",   # CBR 192 kbps; VBR "0" gave ~190 kbps anyway
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
