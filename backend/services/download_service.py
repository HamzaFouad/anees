from __future__ import annotations
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from backend.models import Playlist, Video
from backend.commands.ytdlp import YtdlpClient
from backend.services.split_service import SplitService
from backend.services.speed_service import SpeedService

# Lines from ffmpeg that carry no actionable information for the user
_FFMPEG_NOISE = re.compile(
    r"^(ffmpeg version\s|built with\s|configuration:\s|lib\w+\s+\d"
    r"|Input #\d|Output #\d|Stream #\d|Stream mapping"
    r"|\s+Duration:\s|\s+Metadata\s*:|\s+encoder\s*:"
    r"|\s+Stream #|\s+Copyright|\s+Press \[q\]"
    r"|frame=\s*\d.*fps=|video:\s*\d|audio:\s*\d|subtitle:\s*\d)",
    re.IGNORECASE,
)


def _safe_name(s: str, maxlen: int = 60) -> str:
    return re.sub(r'[^\w\s-]', '_', s).strip('_ ')[:maxlen].strip()


def _playlist_folder(pl: Playlist) -> str:
    """e.g. '00_Andrew Huberman Sleep Toolkit'"""
    return f"{pl.prefix}_{_safe_name(pl.title)}"


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

        folder = _playlist_folder(pl)
        self._log("info", f"Downloading {len(pl.videos)} videos → {self._root}/{folder}/")
        self._download(pl)

    def _download(self, pl: Playlist) -> None:
        _done_fps: set[str] = set()    # dedup by MP3 filepath
        _logged_pct: list[int] = [-1]  # last milestone logged (reset per video)

        # One background worker: split of video N runs concurrently with the
        # download of video N+1.  max_workers=1 keeps CPU pressure predictable
        # while still fully overlapping network I/O with ffmpeg split work.
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="split")

        def _ffmpeg_log(m: str) -> None:
            if _FFMPEG_NOISE.match(m.strip()):
                return
            lvl = "error" if m.strip().lower().startswith("error") else "debug"
            self._log(lvl, m)

        out_tmpl = os.path.join(
            self._root,
            _playlist_folder(pl),
            "%(playlist_index)02d_%(title).60s.%(ext)s",
        )

        def on_progress(d: dict) -> None:
            status = d.get("status")
            info   = d.get("info_dict") or {}
            idx    = max(0, int(info.get("playlist_index") or 1) - 1)
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                done  = d.get("downloaded_bytes") or 0
                pct   = min(int(done / total * 100), 99)
                milestone = (pct // 25) * 25
                if milestone > _logged_pct[0]:
                    _logged_pct[0] = milestone
                    speed = d.get("speed")
                    spd   = f"  {speed/1024/1024:.1f} MB/s" if speed else ""
                    self._log("debug", f"[{idx+1}] downloading {pct}%{spd}")
                self._on_video_stage(pl.id, idx, "download", min(done / total, 0.99))
            elif status == "finished":
                _logged_pct[0] = -1
                self._on_video_stage(pl.id, idx, "mp3", 0.5)
                self._log("debug", f"[{idx+1}] converting to mono MP3…")

        def _do_postprocess(idx: int, title: str, filepath: str) -> None:
            """Runs in the thread pool — concurrent with the NEXT video's download.

            Handles split → speed in sequence. Either or both may be skipped
            depending on playlist settings.
            """
            if self._stop.is_set():
                self._on_video_stage(pl.id, idx, "done", 1.0)
                return

            files = [filepath]

            if pl.split_enabled:
                try:
                    files = SplitService(on_log=_ffmpeg_log).split_file(
                        filepath, pl.split_min, self._stop
                    )
                    self._log("info", f"[{idx+1}] {title}  → {len(files)} part(s)")
                except Exception as exc:
                    self._log("error", f"[{idx+1}] split failed: {exc}")

            if pl.speed != 1.0 and not self._stop.is_set():
                self._on_video_stage(pl.id, idx, "speed", 0.1)
                try:
                    SpeedService(on_log=_ffmpeg_log).apply_speed(files, pl.speed, self._stop)
                    self._log("info", f"[{idx+1}] ×{pl.speed} applied to {len(files)} file(s)")
                except Exception as exc:
                    self._log("error", f"[{idx+1}] speed failed: {exc}")

            # Always advance to "done" — even if a step failed the files still exist
            self._on_video_stage(pl.id, idx, "done", 1.0)

        def on_postprocess(d: dict) -> None:
            if d.get("status") != "finished":
                return
            info     = d.get("info_dict") or {}
            filepath = info.get("filepath") or ""

            # Check the file directly — avoids depending on postprocessor key
            # name which differs between yt-dlp versions
            if not filepath.lower().endswith(".mp3") or not os.path.exists(filepath):
                return
            if filepath in _done_fps:
                return
            _done_fps.add(filepath)

            idx      = max(0, int(info.get("playlist_index") or 1) - 1)
            title    = info.get("title") or f"Video {idx+1}"
            duration = int(info.get("duration") or 0)
            size_mb  = os.path.getsize(filepath) / 1024 / 1024

            self._on_video_meta(pl.id, idx, title, duration)

            needs_postproc = (pl.split_enabled or pl.speed != 1.0) and not self._stop.is_set()
            if needs_postproc:
                # Advance UI to the first active post-processing stage immediately,
                # then return so yt-dlp starts downloading the NEXT video right away.
                # _do_postprocess() runs in the thread pool and emits "done" when finished.
                first_stage = "split" if pl.split_enabled else "speed"
                self._on_video_stage(pl.id, idx, first_stage, 0.1)
                executor.submit(_do_postprocess, idx, title, filepath)
            else:
                self._log("info", f"[{idx+1}] {title}  ({size_mb:.1f} MB)")
                self._on_video_stage(pl.id, idx, "done", 1.0)


        try:
            self._client.download(
                pl.url, out_tmpl,
                on_progress, on_postprocess,
                self._stop, self._pause,
                on_log=lambda lvl, msg: self._log(lvl, msg),
            )
        except Exception as exc:
            self._log("error", f"Download failed: {pl.title} — {exc}")
        finally:
            # Drain all pending/running splits before _download() returns.
            # When _stop is set, split threads exit quickly (ffmpeg is killed).
            executor.shutdown(wait=True)
