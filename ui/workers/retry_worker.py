from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from backend.api.download import DownloadAPI
from backend.models import Playlist, Video


class RetryVideoWorker(QThread):
    video_stage = Signal(str, int, str, float)   # pid, idx, stage, progress
    video_meta  = Signal(str, int, str, int)     # pid, idx, title, duration_sec
    log_added   = Signal(str, str, str)          # level, src, msg
    completed   = Signal()

    def __init__(self, pl: Playlist, video_idx: int, output_root: str, parent=None):
        super().__init__(parent)
        self._pl         = pl
        self._video_idx  = video_idx
        self._output_root = output_root
        self._api: DownloadAPI | None = None

    def run(self) -> None:
        self._api = DownloadAPI(
            output_root    = self._output_root,
            on_video_stage = lambda pid, idx, stage, pct: self.video_stage.emit(pid, idx, stage, pct),
            on_video_meta  = lambda pid, idx, title, dur: self.video_meta.emit(pid, idx, title, dur),
            on_log         = lambda lvl, src, msg: self.log_added.emit(lvl, src, msg),
        )
        self._api.retry_video(self._pl, self._video_idx)
        self.completed.emit()

    def stop(self) -> None:
        if self._api:
            self._api.stop()
