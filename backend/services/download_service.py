from __future__ import annotations
import os
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from backend.models import Playlist, Video
from backend.commands.ytdlp import YtdlpClient
from backend.services.split_service import SplitService
from backend.services.speed_service import SpeedService
from backend.types import VideoStage, PlaylistStatus
from backend.errors import DownloadFailedError, InvalidOutputFolderError

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
        client:          YtdlpClient | None = None,
        stop_event:      threading.Event | None = None,
        pause_event:     threading.Event | None = None,
        split_service_factory: Callable[[Callable[[str], None]], SplitService] | None = None,
        speed_service_factory: Callable[[Callable[[str], None]], SpeedService] | None = None,
    ):
        self._root            = output_root or str(Path.home() / "Downloads" / "Anees")
        self._on_videos_ready = on_videos_ready or (lambda *_: None)
        self._on_video_stage  = on_video_stage  or (lambda *_: None)
        self._on_video_meta   = on_video_meta   or (lambda *_: None)
        self._on_log          = on_log          or (lambda *_: None)
        self._on_complete     = on_complete     or (lambda: None)
        self._client       = client or YtdlpClient()
        self._stop         = stop_event or threading.Event()
        self._pause        = pause_event or threading.Event()
        self._make_split_service = split_service_factory or (lambda on_log: SplitService(on_log=on_log))
        self._make_speed_service = speed_service_factory or (lambda on_log: SpeedService(on_log=on_log))
        self._pause.set()

    # ── Public control ────────────────────────────────────────────────────────
    def execute(self, playlists: list[Playlist]) -> None:
        self._stop.clear()
        try:
            Path(self._root).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            err = InvalidOutputFolderError(
                technical_message=f"Cannot create output folder: {self._root} — {exc}"
            )
            self._log("error", f"{err.user_message} ({err.code})")
            self._log("debug", err.technical_message)
            self._on_complete()
            return
        self._log("info", f"Run started — output: {self._root}")

        for pl in playlists:
            if self._stop.is_set():
                break
            if pl.status == PlaylistStatus.DONE:
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
        if pl.source == "local":
            self._run_local_playlist(pl)
            return
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

        pending = self._scan_existing(pl)

        # Apply range filter (1-based, inclusive on both ends).
        # pl.videos may already be sliced to the range, so derive r_end from
        # pl.range_end rather than len(pl.videos) to get the correct absolute end.
        r_start   = pl.range_start or 1
        r_end     = pl.range_end if pl.range_end else (r_start + len(pl.videos) - 1)
        has_range = bool(pl.range_start or pl.range_end)
        if has_range:
            pending = [i for i in pending if r_start <= i <= r_end]
        range_total = r_end - r_start + 1

        if not pending:
            self._log("info", f"{pl.title} — all video(s) in range {r_start}–{r_end} already on disk, skipping")
            return

        already = range_total - len(pending)
        if already:
            self._log("info", f"Resuming — {already}/{range_total} already downloaded (range {r_start}–{r_end}), fetching {len(pending)} remaining")
        elif has_range:
            self._log("info", f"Range {r_start}–{r_end} ({range_total} video(s))")

        playlist_items = ",".join(str(i) for i in pending) if (already or has_range) else None
        folder = _playlist_folder(pl)
        self._log("info", f"Downloading {len(pending)} video(s) → {self._root}/{folder}/")
        self._download(pl, playlist_items=playlist_items)

    def _scan_existing(self, pl: Playlist) -> list[int]:
        """Scan the playlist output folder for already-processed MP3s.

        The highest-index file found is deleted and re-queued for download:
        it was the last video being processed when the run was stopped and
        may be truncated or corrupted. All lower-index files are trusted.

        Marks confirmed-complete videos as done via _on_video_stage.
        Returns the list of 1-based yt-dlp playlist indices still needing download.
        """
        folder_path = os.path.join(self._root, _playlist_folder(pl))
        if not os.path.isdir(folder_path):
            return list(range(1, len(pl.videos) + 1))
        try:
            existing = set(os.listdir(folder_path))
        except OSError:
            return list(range(1, len(pl.videos) + 1))

        # Use absolute 1-based playlist indices (files are named by playlist_index,
        # e.g. range 5–10 produces 05_…mp3 … 10_…mp3, not 01_…mp3).
        r_start = pl.range_start or 1
        found: list[int] = []   # absolute 1-based indices with files on disk
        for i in range(len(pl.videos)):
            abs_idx = r_start + i
            prefix  = f"{abs_idx:02d}_"
            if any(
                f.startswith(prefix) and f.endswith(".mp3") and not f.endswith(".spd.mp3")
                for f in existing
            ):
                found.append(abs_idx)

        if not found:
            return [r_start + i for i in range(len(pl.videos))]

        # Delete the last found file(s) — may have been interrupted mid-processing
        last = max(found)
        last_prefix = f"{last:02d}_"
        for fname in existing:
            if fname.startswith(last_prefix) and fname.endswith(".mp3"):
                try:
                    os.remove(os.path.join(folder_path, fname))
                    self._log("info", f"[{last}] deleted possibly-incomplete file — will re-download")
                except OSError as exc:
                    self._log("warn", f"[{last}] could not delete {fname}: {exc}")
        found.remove(last)

        # Mark confirmed-complete videos as done using relative (0-based) indices
        for abs_idx in found:
            self._on_video_stage(pl.id, abs_idx - r_start, VideoStage.DONE, 1.0)

        # pending = every absolute index not confirmed complete (including the deleted last)
        confirmed = set(found)
        return [r_start + i for i in range(len(pl.videos)) if (r_start + i) not in confirmed]

    def _run_local_playlist(self, pl: Playlist) -> None:
        """Process a local folder source — copy each MP3, then run split/speed pipeline."""
        folder = Path(pl.url)
        if not folder.is_dir():
            self._log("error", f"Local folder not found: {pl.url}")
            return

        files = sorted(folder.glob("*.mp3"))
        if not files:
            self._log("error", f"No MP3 files in: {pl.url}")
            return

        out_dir = Path(self._root) / _playlist_folder(pl)
        out_dir.mkdir(parents=True, exist_ok=True)
        self._log("info", f"Local folder: {len(files)} file(s) → {out_dir}")

        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="split")

        def _ffmpeg_log(m: str) -> None:
            if _FFMPEG_NOISE.match(m.strip()):
                return
            lvl = "error" if m.strip().lower().startswith("error") else "debug"
            self._log(lvl, m)

        def _mark_failed(idx: int, error_msg: str) -> None:
            if idx < len(pl.videos):
                v = pl.videos[idx]
                v.error = error_msg
            self._on_video_stage(pl.id, idx, VideoStage.FAILED, 0.0)
            self._log("error", f"[{idx+1}] failed: {error_msg}")

        def _do_postprocess(idx: int, title: str, filepath: str) -> None:
            if self._stop.is_set():
                self._on_video_stage(pl.id, idx, VideoStage.DONE, 1.0)
                return

            files_to_process = [filepath]

            if pl.split_enabled:
                try:
                    files_to_process = self._make_split_service(_ffmpeg_log).split_file(
                        filepath, pl.split_min, self._stop
                    )
                    self._log("info", f"[{idx+1}] {title}  → {len(files_to_process)} part(s)")
                except Exception as exc:
                    _mark_failed(idx, f"Split failed: {exc}")
                    return

            if pl.speed != 1.0 and not self._stop.is_set():
                self._on_video_stage(pl.id, idx, VideoStage.SPEED, 0.1)
                try:
                    self._make_speed_service(_ffmpeg_log).apply_speed(files_to_process, pl.speed, self._stop)
                    self._log("info", f"[{idx+1}] ×{pl.speed} applied to {len(files_to_process)} file(s)")
                except Exception as exc:
                    _mark_failed(idx, f"Speed ×{pl.speed} failed: {exc}")
                    return

            self._on_video_stage(pl.id, idx, VideoStage.DONE, 1.0)

        try:
            for idx, src in enumerate(files):
                if self._stop.is_set():
                    break
                self._pause.wait()

                title = src.stem
                dest = out_dir / f"{idx+1:02d}_{src.name}"

                self._on_video_stage(pl.id, idx, VideoStage.DOWNLOAD, 0.5)
                try:
                    shutil.copy2(str(src), str(dest))
                except OSError as exc:
                    _mark_failed(idx, f"Copy failed: {exc}")
                    continue

                self._on_video_stage(pl.id, idx, VideoStage.MP3, 1.0)
                size_mb = dest.stat().st_size / 1024 / 1024
                dur = pl.videos[idx].duration_sec if idx < len(pl.videos) else 0
                self._on_video_meta(pl.id, idx, title, dur)

                needs_postproc = (pl.split_enabled or pl.speed != 1.0) and not self._stop.is_set()
                if needs_postproc:
                    first_stage = VideoStage.SPLIT if pl.split_enabled else VideoStage.SPEED
                    self._on_video_stage(pl.id, idx, first_stage, 0.1)
                    executor.submit(_do_postprocess, idx, title, str(dest))
                else:
                    self._log("info", f"[{idx+1}] {title}  ({size_mb:.1f} MB)")
                    self._on_video_stage(pl.id, idx, VideoStage.DONE, 1.0)
        finally:
            executor.shutdown(wait=True)

    def retry_videos(self, pl: Playlist, playlist_items: str) -> None:
        """Re-download specific videos by a 1-based playlist_items string (e.g. '2,4,7')."""
        self._stop.clear()
        self._pause.set()
        self._download(pl, playlist_items=playlist_items)

    def _download(self, pl: Playlist, playlist_items: str | None = None) -> None:
        _done_fps: set[str] = set()    # dedup by MP3 filepath
        _logged_pct: list[int] = [-1]  # last milestone logged (reset per video)
        # yt-dlp reports playlist_index as an absolute 1-based position in the full
        # playlist; subtract this offset so idx maps into the (possibly sliced) pl.videos.
        _idx_offset = (pl.range_start or 1) - 1

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

        def _mark_failed(idx: int, error_msg: str) -> None:
            if idx < len(pl.videos):
                v = pl.videos[idx]
                v.failed_at = v.stage if v.stage not in ("queued", "failed") else "download"
                v.error = error_msg
            self._on_video_stage(pl.id, idx, VideoStage.FAILED, 0.0)
            self._log("error", f"[{idx+1}] failed: {error_msg}")

        def on_progress(d: dict) -> None:
            status = d.get("status")
            info   = d.get("info_dict") or {}
            idx    = max(0, int(info.get("playlist_index") or 1) - 1 - _idx_offset)

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
                self._on_video_stage(pl.id, idx, VideoStage.DOWNLOAD, min(done / total, 0.99))
            elif status == "finished":
                _logged_pct[0] = -1
                self._on_video_stage(pl.id, idx, VideoStage.MP3, 0.5)
                self._log("debug", f"[{idx+1}] converting to mono MP3…")
            elif status == "error":
                error_msg = str(d.get("error") or "Download failed")
                _mark_failed(idx, error_msg)

        def _do_postprocess(idx: int, title: str, filepath: str) -> None:
            """Runs in the thread pool — concurrent with the NEXT video's download.

            Handles split → speed in sequence. Either or both may be skipped.
            Failures call _mark_failed so the row shows the broken stage + error.
            """
            if self._stop.is_set():
                self._on_video_stage(pl.id, idx, VideoStage.DONE, 1.0)
                return

            files = [filepath]

            if pl.split_enabled:
                try:
                    files = self._make_split_service(_ffmpeg_log).split_file(
                        filepath, pl.split_min, self._stop
                    )
                    self._log("info", f"[{idx+1}] {title}  → {len(files)} part(s)")
                except Exception as exc:
                    _mark_failed(idx, f"Split failed: {exc}")
                    return

            if pl.speed != 1.0 and not self._stop.is_set():
                self._on_video_stage(pl.id, idx, VideoStage.SPEED, 0.1)
                try:
                    self._make_speed_service(_ffmpeg_log).apply_speed(files, pl.speed, self._stop)
                    self._log("info", f"[{idx+1}] ×{pl.speed} applied to {len(files)} file(s)")
                except Exception as exc:
                    _mark_failed(idx, f"Speed ×{pl.speed} failed: {exc}")
                    return

            self._on_video_stage(pl.id, idx, VideoStage.DONE, 1.0)

        def on_postprocess(d: dict) -> None:
            status = d.get("status")
            info   = d.get("info_dict") or {}

            # Postprocessor failure (e.g. ffmpeg not found, corrupt audio)
            if status == "error":
                error_msg = str(d.get("error") or
                                f"{d.get('postprocessor', 'postprocessor')} failed")
                idx = max(0, int(info.get("playlist_index") or 1) - 1 - _idx_offset)
                _mark_failed(idx, error_msg)
                return

            if status != "finished":
                return
            filepath = info.get("filepath") or ""
            # Check the file directly — avoids depending on postprocessor key
            # name which differs between yt-dlp versions
            if not filepath.lower().endswith(".mp3") or not os.path.exists(filepath):
                return
            if filepath in _done_fps:
                return
            _done_fps.add(filepath)

            idx      = max(0, int(info.get("playlist_index") or 1) - 1 - _idx_offset)
            title    = info.get("title") or f"Video {idx+1}"
            duration = int(info.get("duration") or 0)
            size_mb  = os.path.getsize(filepath) / 1024 / 1024

            self._on_video_meta(pl.id, idx, title, duration)

            needs_postproc = (pl.split_enabled or pl.speed != 1.0) and not self._stop.is_set()
            if needs_postproc:
                # Advance UI to the first active post-processing stage immediately,
                # then return so yt-dlp starts downloading the NEXT video right away.
                # _do_postprocess() runs in the thread pool and emits "done" when finished.
                first_stage = VideoStage.SPLIT if pl.split_enabled else VideoStage.SPEED
                self._on_video_stage(pl.id, idx, first_stage, 0.1)
                executor.submit(_do_postprocess, idx, title, filepath)
            else:
                self._log("info", f"[{idx+1}] {title}  ({size_mb:.1f} MB)")
                self._on_video_stage(pl.id, idx, VideoStage.DONE, 1.0)


        try:
            self._client.download(
                pl.url, out_tmpl,
                on_progress, on_postprocess,
                self._stop, self._pause,
                on_log=lambda lvl, msg: self._log(lvl, msg),
                playlist_items=playlist_items,
            )
        except Exception as exc:
            err = DownloadFailedError(
                technical_message=f"Download failed: {pl.title} — {exc}"
            )
            self._log("error", f"{err.user_message} ({err.code})")
            self._log("debug", err.technical_message)
        finally:
            # Drain all pending/running splits before _download() returns.
            # When _stop is set, split threads exit quickly (ffmpeg is killed).
            executor.shutdown(wait=True)
