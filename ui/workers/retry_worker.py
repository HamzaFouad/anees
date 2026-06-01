from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from backend.api.download import DownloadAPI
from backend.models import Playlist


class RetryVideoWorker(QThread):
    video_stage = Signal(str, int, str, float)
    video_meta  = Signal(str, int, str, int)
    log_added   = Signal(str, str, str)
    completed   = Signal()

    def __init__(self, pl: Playlist, video_indices: list[int],
                 output_root: str, parent=None):
        super().__init__(parent)
        self._pl            = pl
        self._video_indices = video_indices
        self._output_root   = output_root
        self._api: DownloadAPI | None = None

    def run(self) -> None:
        self._api = DownloadAPI(
            output_root    = self._output_root,
            on_video_stage = lambda pid, idx, stage, pct: self.video_stage.emit(pid, idx, stage, pct),
            on_video_meta  = lambda pid, idx, title, dur: self.video_meta.emit(pid, idx, title, dur),
            on_log         = lambda lvl, src, msg: self.log_added.emit(lvl, src, msg),
        )
        # 1-based, comma-separated list yt-dlp understands
        playlist_items = ",".join(str(i + 1) for i in sorted(self._video_indices))
        self._api.retry_videos(self._pl, playlist_items)
        self.completed.emit()

    def stop(self) -> None:
        if self._api:
            self._api.stop()
