from __future__ import annotations
import copy
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from backend.models import Playlist, Video, LogEntry, RunState
from backend.mock_data import MOCK_LOGS


class AppState(QObject):
    run_state_changed = Signal(RunState)
    playlists_changed = Signal()
    selection_changed = Signal(str)
    view_changed      = Signal(str)
    query_changed     = Signal(str)
    logs_changed      = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run_state = RunState.IDLE
        self._playlists: list[Playlist] = []
        self._selected  = ""
        self._view      = "queue"
        self._query     = ""
        self._logs: list[LogEntry] = copy.deepcopy(MOCK_LOGS)
        self._worker    = None
        self._output_root = str(Path.home() / "Downloads" / "Anees")

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

    def counts(self) -> dict:
        queued = sum(1 for p in self._playlists if p.status in ("queued", "active"))
        done   = sum(1 for p in self._playlists if p.status == "done")
        vdone  = sum(p.completed for p in self._playlists)
        vtotal = sum(p.video_count for p in self._playlists)
        return {"queued": queued, "done": done, "videos_done": vdone, "videos_total": vtotal}

    # ── Run lifecycle ─────────────────────────────────────────────────────────
    def start_run(self) -> None:
        from ui.workers.download_worker import DownloadWorker
        pending = [p for p in self._playlists if p.status != "done"]
        print(f"[state] start_run called — pending={len(pending)}", flush=True)
        if not pending:
            print("[state] no pending playlists, aborting", flush=True)
            return
        self._worker = DownloadWorker(pending, self._output_root, self)
        self._worker.videos_ready.connect(self._on_videos_ready)
        self._worker.video_stage.connect(self._on_video_stage)
        self._worker.log_added.connect(self._add_log)
        self._worker.run_complete.connect(self._on_run_complete)
        self._worker.start()
        self._set_run_state(RunState.RUNNING)

    def pause_run(self) -> None:
        if self._worker:
            self._worker.pause()
        self._set_run_state(RunState.PAUSED)

    def resume_run(self) -> None:
        if self._worker:
            self._worker.resume()
        self._set_run_state(RunState.RUNNING)

    def stop_run(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.wait(3000)
            self._worker = None
        # reset active playlists back to queued
        for p in self._playlists:
            if p.status == "active":
                p.status = "queued"
        self.playlists_changed.emit()
        self._set_run_state(RunState.IDLE)

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
    def _on_videos_ready(self, pid: str, videos) -> None:
        print(f"[state] videos_ready received — pid={pid} count={len(videos)}", flush=True)
        pl = self._playlist(pid)
        if not pl:
            return
        pl.videos      = list(videos)
        pl.video_count = len(videos)
        pl.status      = "active"
        self.playlists_changed.emit()
        if pid == self._selected:
            self.selection_changed.emit(pid)

    def _on_video_stage(self, pid: str, idx: int, stage: str, progress: float) -> None:
        pl = self._playlist(pid)
        if not pl or idx < 0:
            return
        # extend video list if needed (yt-dlp can report more items than info fetch)
        while idx >= len(pl.videos):
            pl.videos.append(Video(title=f"Video {len(pl.videos)+1}", duration_sec=0, stage="queued"))
        v = pl.videos[idx]
        v.stage    = stage
        v.progress = progress
        if stage == "done":
            pl.completed = sum(1 for vv in pl.videos if vv.stage == "done")
            pl.status    = "done" if pl.completed >= pl.video_count else "active"
        pl.active_stage = stage
        self.playlists_changed.emit()
        if pid == self._selected:
            self.selection_changed.emit(pid)

    def _on_run_complete(self) -> None:
        self._worker = None
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

    def add_playlist(self, pl: Playlist) -> None:
        self._playlists.append(pl)
        self._selected = pl.id
        self.playlists_changed.emit()
        self.selection_changed.emit(pl.id)

    def remove_playlist(self, pid: str) -> None:
        self._playlists = [p for p in self._playlists if p.id != pid]
        if self._selected == pid:
            self._selected = self._playlists[0].id if self._playlists else ""
            self.selection_changed.emit(self._selected)
        self.playlists_changed.emit()

    def _playlist(self, pid: str) -> Playlist | None:
        return next((p for p in self._playlists if p.id == pid), None)
