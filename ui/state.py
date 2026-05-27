from __future__ import annotations
from PySide6.QtCore import QObject, Signal
from backend.models import Playlist, RunState
from backend.mock_data import MOCK_PLAYLISTS, SAMPLE_VIDEOS
import copy


class AppState(QObject):
    run_state_changed  = Signal(RunState)
    playlists_changed  = Signal()
    selection_changed  = Signal(str)   # selected playlist id
    view_changed       = Signal(str)   # queue / history / logs
    query_changed      = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._run_state  = RunState.IDLE
        self._playlists  = copy.deepcopy(MOCK_PLAYLISTS)
        self._selected   = self._playlists[0].id if self._playlists else ""
        self._view       = "queue"
        self._query      = ""

    # ── Accessors ─────────────────────────────────────────────────────────────
    @property
    def run_state(self) -> RunState:
        return self._run_state

    @property
    def playlists(self) -> list[Playlist]:
        return self._playlists

    @property
    def selected_id(self) -> str:
        return self._selected

    @property
    def view(self) -> str:
        return self._view

    @property
    def query(self) -> str:
        return self._query

    @property
    def locked(self) -> bool:
        return self._run_state in (RunState.RUNNING, RunState.PAUSED)

    def selected_playlist(self) -> Playlist | None:
        return next((p for p in self._playlists if p.id == self._selected), None)

    def counts(self) -> dict:
        queued = sum(1 for p in self._playlists if p.status in ("queued", "active"))
        done   = sum(1 for p in self._playlists if p.status == "done")
        vdone  = sum(p.completed for p in self._playlists)
        vtotal = sum(p.video_count for p in self._playlists)
        return {"queued": queued, "done": done, "videos_done": vdone, "videos_total": vtotal}

    # ── Mutations ─────────────────────────────────────────────────────────────
    def set_run_state(self, state: RunState):
        self._run_state = state
        self.run_state_changed.emit(state)

    def set_view(self, view: str):
        self._view = view
        self.view_changed.emit(view)

    def set_selected(self, pid: str):
        self._selected = pid
        self.selection_changed.emit(pid)

    def set_query(self, q: str):
        self._query = q
        self.query_changed.emit(q)

    def add_playlist(self, pl: Playlist):
        self._playlists.append(pl)
        self._selected = pl.id
        self.playlists_changed.emit()
        self.selection_changed.emit(pl.id)

    def remove_playlist(self, pid: str):
        self._playlists = [p for p in self._playlists if p.id != pid]
        if self._selected == pid:
            self._selected = self._playlists[0].id if self._playlists else ""
            self.selection_changed.emit(self._selected)
        self.playlists_changed.emit()

    def reset_queue(self):
        self._playlists = copy.deepcopy(MOCK_PLAYLISTS)
        self._selected  = self._playlists[0].id if self._playlists else ""
        self.playlists_changed.emit()
        self.selection_changed.emit(self._selected)
