from __future__ import annotations
import threading
from typing import Callable

from backend.models import Video
from backend.platform.tools import ffmpeg_exe


def _find_ffmpeg() -> str:
    """Compatibility shim: delegate lookup to platform layer."""
    return ffmpeg_exe()


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

    def fetch_video_urls(self, playlist_url: str) -> list[tuple[str, str, int]]:
        """Return [(webpage_url, title, duration_sec)] for every entry in a playlist."""
        import yt_dlp
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        result: list[tuple[str, str, int]] = []
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
            for e in (info.get("entries") or []):
                if not e:
                    continue
                url = e.get("webpage_url") or e.get("url") or ""
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                if url:
                    result.append((url, e.get("title") or "", int(e.get("duration") or 0)))
        except Exception as exc:
            raise RuntimeError(f"fetch_video_urls failed: {exc}") from exc
        return result

    # ── Download ──────────────────────────────────────────────────────────────
    def download(
        self,
        url: str,
        output_template: str,
        on_progress:    Callable[[dict], None],
        on_postprocess: Callable[[dict], None],
        stop:           threading.Event,
        pause:          threading.Event,
        on_log:         Callable[[str, str], None] | None = None,
        playlist_items: str | None = None,
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

        # yt-dlp logger — surfaces warnings/errors and [download] progress lines
        # when on_log is provided; quiet stays True so raw output goes nowhere else
        if on_log:
            class _Logger:
                def debug(self, msg):
                    # [download] lines carry speed / ETA / progress text
                    if msg.startswith("[download]") or msg.startswith("[info]"):
                        on_log("debug", msg)
                def info(self, msg):   on_log("info",  msg)
                def warning(self, msg): on_log("warn", msg)
                def error(self, msg):  on_log("error", msg)
            logger = _Logger()
        else:
            logger = None

        ffmpeg = _find_ffmpeg()
        opts = {
            "format":          "bestaudio/best",
            "ffmpeg_location": ffmpeg,
            "postprocessors":  [
                {
                    "key":              "FFmpegExtractAudio",
                    "preferredcodec":   "mp3",
                    "preferredquality": "192",
                },
            ],
            "postprocessor_args":  {"ffmpegextractaudio": ["-ac", "1"]},
            "outtmpl":             output_template,
            "ignoreerrors":        True,
            "quiet":               True,
            **({"logger": logger} if logger else {}),
            "no_warnings":         True,
            "progress_hooks":      [_progress],
            "postprocessor_hooks": [on_postprocess],
            **({"playlist_items": playlist_items} if playlist_items else {}),
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except yt_dlp.utils.DownloadCancelled:
            pass   # normal stop — caller already set stop flag
        except Exception as exc:
            if on_log:
                on_log("error", f"yt-dlp: {exc}")
            raise
