from __future__ import annotations
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

import yt_dlp

from backend.models import Playlist, Video
from backend.commands.ytdlp import make_info_opts, make_download_opts


class DownloadService:
    def __init__(
        self,
        output_root: str | None = None,
        on_videos_ready: Callable[[str, list[Video]], None] | None = None,
        on_video_stage:  Callable[[str, int, str, float], None] | None = None,
        on_log:          Callable[[str, str, str], None] | None = None,
        on_complete:     Callable[[], None] | None = None,
    ):
        self._root           = output_root or str(Path.home() / "Downloads" / "Anees")
        self._on_videos_ready = on_videos_ready or (lambda *_: None)
        self._on_video_stage  = on_video_stage  or (lambda *_: None)
        self._on_log          = on_log          or (lambda *_: None)
        self._on_complete     = on_complete     or (lambda: None)
        self._stop  = threading.Event()
        self._pause = threading.Event()
        self._pause.set()        # not paused initially
        self._current_idx = 0    # 0-based index of video being downloaded

    # ── Public control ────────────────────────────────────────────────────────
    def execute(self, playlists: list[Playlist]) -> None:
        self._stop.clear()
        Path(self._root).mkdir(parents=True, exist_ok=True)

        for pl in playlists:
            if self._stop.is_set():
                break
            if pl.status == "done":
                continue
            self._run_playlist(pl)

        if not self._stop.is_set():
            self._on_complete()

    def stop(self)   -> None: self._stop.set();  self._pause.set()
    def pause(self)  -> None: self._pause.clear()
    def resume(self) -> None: self._pause.set()

    # ── Per-playlist ──────────────────────────────────────────────────────────
    def _run_playlist(self, pl: Playlist) -> None:
        # Fetch metadata if videos are still placeholder
        if not pl.videos or all(v.title.startswith("Video ") for v in pl.videos):
            videos = self._fetch_info(pl.url)
            if videos:
                self._on_videos_ready(pl.id, videos)

        if self._stop.is_set():
            return

        self._download(pl)

    def _fetch_info(self, url: str) -> list[Video]:
        videos: list[Video] = []
        try:
            with yt_dlp.YoutubeDL(make_info_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
                for entry in (info.get("entries") or []):
                    if entry:
                        videos.append(Video(
                            title       = entry.get("title") or f"Video {len(videos)+1}",
                            duration_sec= int(entry.get("duration") or 0),
                            stage       = "queued",
                        ))
        except Exception as exc:
            self._on_log("warn", "yt-dlp", f"Metadata fetch failed: {exc}")
        return videos

    def _download(self, pl: Playlist) -> None:
        self._current_idx = 0
        self._pl_id = pl.id
        out_dir = self._root

        def hook(d: dict) -> None:
            self._pause.wait()                   # block while paused
            if self._stop.is_set():
                raise yt_dlp.utils.DownloadCancelled("stopped by user")

            status = d.get("status")
            idx    = self._current_idx

            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                done  = d.get("downloaded_bytes") or 0
                pct   = min(done / total, 0.99)
                self._on_video_stage(pl.id, idx, "download", pct)

            elif status == "finished":
                # download done, post-processor (mp3 conversion) starting
                self._on_video_stage(pl.id, idx, "mp3", 0.5)

        def postprocess_hook(d: dict) -> None:
            if d.get("status") == "finished":
                idx = self._current_idx
                self._on_video_stage(pl.id, idx, "done", 1.0)
                self._current_idx += 1

        opts = make_download_opts(pl, out_dir, hook)
        opts["postprocessor_hooks"] = [postprocess_hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([pl.url])
        except yt_dlp.utils.DownloadCancelled:
            self._on_log("info", "yt-dlp", f"Download stopped: {pl.title}")
        except Exception as exc:
            self._on_log("error", "yt-dlp", f"Download failed: {pl.title} — {exc}")
