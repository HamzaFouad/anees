from __future__ import annotations
import threading
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
        self._root            = output_root or str(Path.home() / "Downloads" / "Anees")
        self._on_videos_ready = on_videos_ready or (lambda *_: None)
        self._on_video_stage  = on_video_stage  or (lambda *_: None)
        self._on_log          = on_log          or (lambda *_: None)
        self._on_complete     = on_complete     or (lambda: None)
        self._stop  = threading.Event()
        self._pause = threading.Event()
        self._pause.set()
        self._current_idx = 0

    # ── Public control ────────────────────────────────────────────────────────
    def execute(self, playlists: list[Playlist]) -> None:
        self._stop.clear()
        Path(self._root).mkdir(parents=True, exist_ok=True)
        self._log("info", f"Run started — output: {self._root}")

        for pl in playlists:
            if self._stop.is_set():
                break
            if pl.status == "done":
                self._log("info", f"Skipping (already done): {pl.title}")
                continue
            self._run_playlist(pl)

        if not self._stop.is_set():
            self._log("info", "All playlists complete")
            self._on_complete()

    def stop(self)   -> None: self._stop.set();  self._pause.set()
    def pause(self)  -> None: self._pause.clear()
    def resume(self) -> None: self._pause.set()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _log(self, level: str, msg: str) -> None:
        print(f"[anees/{level}] {msg}", flush=True)
        self._on_log(level, "anees", msg)

    # ── Per-playlist ──────────────────────────────────────────────────────────
    def _run_playlist(self, pl: Playlist) -> None:
        self._log("info", f"Processing: {pl.title}")

        if not pl.videos or all(v.title.startswith("Video ") for v in pl.videos):
            self._log("info", f"Fetching video list from {pl.url} …")
            videos, real_title = self._fetch_info(pl.url)
            if not videos:
                self._log("error", "Info fetch returned no videos — check the URL and network")
                return
            self._log("info", f"Found {len(videos)} videos — '{real_title}'")
            self._on_videos_ready(pl.id, videos, real_title)

        if self._stop.is_set():
            return

        self._log("info", f"Downloading {len(pl.videos)} videos → {self._root}/{pl.prefix}_*")
        self._download(pl)

    def _fetch_info(self, url: str) -> tuple[list[Video], str]:
        """Returns (videos, playlist_title)."""
        videos: list[Video] = []
        playlist_title = ""
        try:
            with yt_dlp.YoutubeDL(make_info_opts()) as ydl:
                info = ydl.extract_info(url, download=False)
                playlist_title = info.get("title") or ""
                for entry in (info.get("entries") or []):
                    if entry:
                        videos.append(Video(
                            title        = entry.get("title") or f"Video {len(videos)+1}",
                            duration_sec = int(entry.get("duration") or 0),
                            stage        = "queued",
                        ))
        except Exception as exc:
            self._log("error", f"Metadata fetch failed: {exc}")
        return videos, playlist_title

    def _download(self, pl: Playlist) -> None:
        self._current_idx = 0
        _done_ids: set[str] = set()

        def hook(d: dict) -> None:
            self._pause.wait()
            if self._stop.is_set():
                raise yt_dlp.utils.DownloadCancelled("stopped by user")

            status = d.get("status")
            idx    = self._current_idx

            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                done  = d.get("downloaded_bytes") or 0
                self._on_video_stage(pl.id, idx, "download", min(done / total, 0.99))

            elif status == "finished":
                self._on_video_stage(pl.id, idx, "mp3", 0.5)

        def postprocess_hook(d: dict) -> None:
            if d.get("status") != "finished":
                return
            info = d.get("info_dict") or {}
            key  = str(info.get("id", "")) + str(info.get("playlist_index", ""))
            if not key or key in _done_ids:
                return
            _done_ids.add(key)
            idx = self._current_idx
            title = info.get("title", f"video {idx+1}")
            self._log("info", f"Done [{idx+1}] {title}")
            self._on_video_stage(pl.id, idx, "done", 1.0)
            self._current_idx += 1

        opts = make_download_opts(pl, self._root, hook)
        opts["postprocessor_hooks"] = [postprocess_hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([pl.url])
        except yt_dlp.utils.DownloadCancelled:
            self._log("info", f"Stopped: {pl.title}")
        except Exception as exc:
            self._log("error", f"Download failed: {pl.title} — {exc}")
