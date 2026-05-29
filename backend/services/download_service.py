from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Callable

from backend.models import Playlist, Video
from backend.commands.ytdlp import YtdlpClient


class DownloadService:
    def __init__(
        self,
        output_root:     str | None = None,
        on_videos_ready: Callable[[str, list[Video]], None] | None = None,
        on_video_stage:  Callable[[str, int, str, float], None] | None = None,
        on_video_meta:   Callable[[str, int, str, int], None] | None = None,
        on_log:          Callable[[str, str, str], None] | None = None,
        on_complete:     Callable[[], None] | None = None,
    ):
        self._root            = output_root or str(Path.home() / "Downloads" / "Anees")
        self._on_videos_ready = on_videos_ready or (lambda *_: None)
        self._on_video_stage  = on_video_stage  or (lambda *_: None)
        self._on_video_meta   = on_video_meta   or (lambda *_: None)
        self._on_log          = on_log          or (lambda *_: None)
        self._on_complete     = on_complete     or (lambda: None)
        self._client  = YtdlpClient()
        self._stop    = threading.Event()
        self._pause   = threading.Event()
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
            try:
                videos, real_title = self._client.fetch_info(pl.url)
            except Exception as exc:
                self._log("error", str(exc))
                return
            if not videos:
                self._log("error", "Info fetch returned no videos — check the URL")
                return
            self._log("info", f"Found {len(videos)} videos — '{real_title}'")
            self._on_videos_ready(pl.id, videos, real_title)

        if self._stop.is_set():
            return

        self._log("info", f"Downloading {len(pl.videos)} videos → {self._root}/{pl.prefix}_*")
        self._download(pl)

    def _download(self, pl: Playlist) -> None:
        self._current_idx = 0
        _done_ids: set[str] = set()

        out_tmpl = os.path.join(
            self._root,
            f"{pl.prefix}_%(playlist_index)02d_%(title).60s.%(ext)s",
        )

        def on_progress(d: dict) -> None:
            status = d.get("status")
            idx    = self._current_idx
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                done  = d.get("downloaded_bytes") or 0
                self._on_video_stage(pl.id, idx, "download", min(done / total, 0.99))
            elif status == "finished":
                self._on_video_stage(pl.id, idx, "mp3", 0.5)

        def on_postprocess(d: dict) -> None:
            if d.get("status") != "finished":
                return
            info  = d.get("info_dict") or {}
            key   = str(info.get("id", "")) + str(info.get("playlist_index", ""))
            if not key or key in _done_ids:
                return
            _done_ids.add(key)
            idx      = self._current_idx
            title    = info.get("title") or f"Video {idx+1}"
            duration = int(info.get("duration") or 0)
            self._log("info", f"Done [{idx+1}] {title}")
            self._on_video_stage(pl.id, idx, "done", 1.0)
            self._on_video_meta(pl.id, idx, title, duration)
            self._current_idx += 1

        try:
            self._client.download(
                pl.url, out_tmpl,
                on_progress, on_postprocess,
                self._stop, self._pause,
            )
        except Exception as exc:
            self._log("error", f"Download failed: {pl.title} — {exc}")
