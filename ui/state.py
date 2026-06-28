from __future__ import annotations
import copy
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from backend.app_state.run_controller import RunController
from backend.models import Playlist, Video, LogEntry, RunState
from backend.mock_data import MOCK_LOGS
from backend.types import PlaylistStatus, VideoStage


class AppState(QObject):
    run_state_changed = Signal(RunState)
    playlists_changed = Signal()
    selection_changed = Signal(str)
    video_row_changed = Signal(str, int)
    view_changed      = Signal(str)
    query_changed     = Signal(str)
    logs_changed      = Signal()
    retry_complete    = Signal()   # emitted after all retry workers finish

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run_state = RunState.IDLE
        self._playlists: list[Playlist] = []
        self._selected  = ""
        self._view      = "queue"
        self._query     = ""
        self._logs: list[LogEntry] = copy.deepcopy(MOCK_LOGS)
        from backend.api import get_output_root
        self._output_root = get_output_root()
        # throttle: batch UI refreshes during active downloads
        self._dirty_pids: set[str] = set()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(300)
        self._refresh_timer.timeout.connect(self._flush_ui)
        self._run_controller = RunController(
            make_download_worker=self._make_download_worker,
            make_retry_worker=self._make_retry_worker,
            make_info_worker=self._make_info_worker,
            on_videos_ready=self._on_videos_ready,
            on_video_stage=self._on_video_stage,
            on_video_meta=self._on_video_meta,
            on_log=self._add_log,
            on_run_complete=self._on_run_complete,
            on_retry_complete=self.retry_complete.emit,
        )

    # ── Accessors ─────────────────────────────────────────────────────────────
    @property
    def run_state(self) -> RunState: return self._run_state
    @property
    def playlists(self) -> list[Playlist]: return self._playlists
    @property
    def selected_id(self) -> str: return self._selected
    @property
    def view(self) -> str: return self._view
    @property
    def query(self) -> str: return self._query
    @property
    def locked(self) -> bool:
        return self._run_state in (RunState.RUNNING, RunState.PAUSED)
    @property
    def logs(self) -> list[LogEntry]: return self._logs

    def selected_playlist(self) -> Playlist | None:
        return next((p for p in self._playlists if p.id == self._selected), None)

    def total_estimate_mb(self) -> float:
        from backend.api import playlist_size_estimate
        return sum(
            playlist_size_estimate(pl)
            for pl in self._playlists
            if pl.status != PlaylistStatus.DONE
        )

    def disk_space_ok(self) -> tuple[bool, float, float]:
        """Returns (ok, required_mb, free_mb) with 20 % safety margin."""
        from backend.api.config import check_disk_space
        return check_disk_space(self.total_estimate_mb(), self._output_root)

    def counts(self) -> dict:
        queued = sum(1 for p in self._playlists if p.status in (PlaylistStatus.QUEUED, PlaylistStatus.ACTIVE))
        done   = sum(1 for p in self._playlists if p.status == PlaylistStatus.DONE)
        vdone   = sum(p.completed for p in self._playlists)
        vtotal  = sum(p.video_count for p in self._playlists)
        vfailed = sum(sum(1 for v in p.videos if v.stage == VideoStage.FAILED) for p in self._playlists)
        return {"queued": queued, "done": done,
                "videos_done": vdone, "videos_total": vtotal, "videos_failed": vfailed}

    # ── Run lifecycle ─────────────────────────────────────────────────────────
    def start_run(self) -> None:
        pending = [p for p in self._playlists if p.status != PlaylistStatus.DONE]
        print(f"[state] start_run called — pending={len(pending)}", flush=True)
        if not pending:
            print("[state] no pending playlists, aborting", flush=True)
            return
        if self._run_controller.start_run(self._playlists, self._output_root):
            self._set_run_state(RunState.RUNNING)

    def pause_run(self) -> None:
        self._run_controller.pause_run()
        self._set_run_state(RunState.PAUSED)

    def resume_run(self) -> None:
        self._run_controller.resume_run()
        self._set_run_state(RunState.RUNNING)

    def stop_run(self) -> None:
        self._run_controller.stop_run(wait_ms=3000)
        # reset active playlists; zero progress on in-progress videos
        # (keep the stage so completed sub-stages retain their checkmarks)
        for p in self._playlists:
            if p.status == PlaylistStatus.ACTIVE:
                p.status = PlaylistStatus.QUEUED
                for v in p.videos:
                    if v.stage not in (VideoStage.DONE, VideoStage.FAILED, VideoStage.QUEUED):
                        v.progress = 0.0  # stage kept — VideoRow renders dot not spinner
        self.playlists_changed.emit()
        self._set_run_state(RunState.IDLE)
        # rebuild detail panel so spinner rows re-render as queued dots
        self.selection_changed.emit(self._selected)

    def retry_video(self, pid: str, video_idx: int) -> None:
        self.retry_videos(pid, [video_idx])

    def retry_videos(self, pid: str, video_indices: list[int]) -> None:
        """Re-download one or more failed videos in a background thread."""
        pl = next((p for p in self._playlists if p.id == pid), None)
        if not pl or not video_indices:
            return
        self._run_controller.retry_videos(pl, video_indices, self._output_root)

    # kept for toolbar compatibility — maps to the right method
    def set_run_state(self, state: RunState) -> None:
        if state == RunState.RUNNING and self._run_state == RunState.IDLE:
            self.start_run()
        elif state == RunState.RUNNING and self._run_state == RunState.PAUSED:
            self.resume_run()
        elif state == RunState.PAUSED:
            self.pause_run()
        elif state == RunState.IDLE:
            self.stop_run()
        else:
            self._set_run_state(state)

    # ── Worker callbacks (called on main thread via queued Signal) ────────────
    def _on_videos_ready(self, pid: str, videos, real_title: str = "") -> None:
        pl = self._playlist(pid)
        if not pl:
            return
        videos = list(videos)
        if pl.range_start or pl.range_end:
            r_start = (pl.range_start or 1) - 1  # 0-based slice start
            r_end   = pl.range_end                # 1-based inclusive = slice end (None = to end)
            videos  = videos[r_start:r_end]
        print(f"[state] videos_ready — pid={pid} count={len(videos)}", flush=True)
        pl.videos      = videos
        pl.video_count = len(videos)
        pl.status      = PlaylistStatus.QUEUED
        if real_title:
            pl.title = real_title
        self.playlists_changed.emit()
        if pid == self._selected:
            self.selection_changed.emit(pid)

    def _on_video_stage(self, pid: str, idx: int, stage: str, progress: float) -> None:
        pl = self._playlist(pid)
        if not pl or idx < 0:
            return
        # extend video list if needed (yt-dlp can report more items than info fetch)
        while idx >= len(pl.videos):
            pl.videos.append(Video(title=f"Video {len(pl.videos)+1}", duration_sec=0, stage=VideoStage.QUEUED))
        v = pl.videos[idx]
        stage_changed = v.stage != stage
        v.stage    = stage
        v.progress = progress
        if stage == VideoStage.DONE:
            pl.completed = sum(1 for vv in pl.videos if vv.stage == VideoStage.DONE)
            pl.status    = PlaylistStatus.DONE if pl.completed >= pl.video_count else PlaylistStatus.ACTIVE
            # sidebar needs updating when a video completes
            self._dirty_pids.add(pid)
            if not self._refresh_timer.isActive():
                self._refresh_timer.start()
        elif pl.status == PlaylistStatus.QUEUED and stage != VideoStage.FAILED:
            # first stage callback marks the playlist as actively running
            pl.status = PlaylistStatus.ACTIVE
            self._dirty_pids.add(pid)
            if not self._refresh_timer.isActive():
                self._refresh_timer.start()
        pl.active_stage = stage
        # emit targeted row update on every stage transition (no throttle — it's a single row)
        if stage_changed:
            self.video_row_changed.emit(pid, idx)

    def _flush_ui(self) -> None:
        """Batched sidebar refresh — runs at most every 300 ms via QTimer."""
        if not self._dirty_pids:
            return
        self.playlists_changed.emit()
        self._dirty_pids.clear()

    def _on_video_meta(self, pid: str, idx: int, title: str, duration_sec: int) -> None:
        pl = self._playlist(pid)
        if not pl or idx < 0 or idx >= len(pl.videos):
            return
        v = pl.videos[idx]
        if title:
            v.title = title
        if duration_sec > 0:
            v.duration_sec = duration_sec
        self.video_row_changed.emit(pid, idx)

    def _on_run_complete(self) -> None:
        self._refresh_timer.stop()
        self._dirty_pids.clear()
        self.playlists_changed.emit()             # sidebar update
        if self._selected:
            self.selection_changed.emit(self._selected)   # final detail panel refresh
        self._set_run_state(RunState.COMPLETE)

    def _add_log(self, level: str, src: str, msg: str) -> None:
        entry = LogEntry(
            t=datetime.now().strftime("%H:%M:%S"),
            lvl=level, src=src, msg=msg,
        )
        self._logs.append(entry)
        self.logs_changed.emit()

    # ── Standard mutations ────────────────────────────────────────────────────
    def _set_run_state(self, state: RunState) -> None:
        self._run_state = state
        self.run_state_changed.emit(state)

    def set_view(self, view: str) -> None:
        self._view = view
        self.view_changed.emit(view)

    def set_selected(self, pid: str) -> None:
        self._selected = pid
        self.selection_changed.emit(pid)

    def set_query(self, q: str) -> None:
        self._query = q
        self.query_changed.emit(q)

    def reorder_playlist(self, pid: str, target_index: int) -> None:
        pls = list(self._playlists)
        src = next((i for i, p in enumerate(pls) if p.id == pid), None)
        if src is None or src == target_index:
            return
        pl = pls.pop(src)
        if src < target_index:
            target_index -= 1
        target_index = max(0, min(target_index, len(pls)))
        pls.insert(target_index, pl)
        from backend.api.config import get_prefix_start
        start = get_prefix_start()
        for i, p in enumerate(pls):
            p.prefix = str(start + i).zfill(2)
        self._playlists = pls
        self.playlists_changed.emit()

    def set_output_root(self, path: str) -> None:
        self._output_root = path
        from backend.api import set_output_root
        set_output_root(path)

    def add_playlist(self, pl: Playlist) -> None:
        self._playlists.append(pl)
        self._selected = pl.id
        self.playlists_changed.emit()
        self.selection_changed.emit(pl.id)
        if pl.source != "local":
            self._fetch_info_async(pl)

    def _fetch_info_async(self, pl: Playlist) -> None:
        self._run_controller.fetch_info_async(pl.id, pl.url)

    def remove_playlist(self, pid: str) -> None:
        self._playlists = [p for p in self._playlists if p.id != pid]
        if self._selected == pid:
            self._selected = self._playlists[0].id if self._playlists else ""
            self.selection_changed.emit(self._selected)
        self.playlists_changed.emit()

    def _playlist(self, pid: str) -> Playlist | None:
        return next((p for p in self._playlists if p.id == pid), None)

    def _make_download_worker(self, playlists: list[Playlist], output_root: str):
        from ui.workers.download_worker import DownloadWorker
        return DownloadWorker(playlists, output_root, self)

    def _make_retry_worker(self, pl: Playlist, video_indices: list[int], output_root: str):
        from ui.workers.retry_worker import RetryVideoWorker
        return RetryVideoWorker(pl, video_indices, output_root, self)

    def _make_info_worker(self, playlist_id: str, url: str):
        from ui.workers.info_worker import InfoWorker
        return InfoWorker(playlist_id, url, self)
