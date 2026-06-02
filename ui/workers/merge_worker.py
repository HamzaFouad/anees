from __future__ import annotations
import threading

from PySide6.QtCore import QThread, Signal

from backend.api.merge import MergeAPI
from backend.models import Playlist


class MergeWorker(QThread):
    progress  = Signal(int, int)   # copied, total
    log_added = Signal(str, str)   # level, message
    completed = Signal(int, object)  # total files, skipped list[str]
    failed    = Signal(str)        # error message

    def __init__(
        self,
        playlists: list[Playlist],
        output_root: str,
        dest_path: str,
        splitter_urls: list[str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._playlists     = playlists
        self._output_root   = output_root
        self._dest_path     = dest_path
        self._splitter_urls = splitter_urls
        self._stop          = threading.Event()

    def run(self) -> None:
        try:
            n, skipped = MergeAPI().merge(
                self._playlists,
                self._output_root,
                self._dest_path,
                splitter_urls=self._splitter_urls,
                on_log=lambda msg: self.log_added.emit("info", msg),
                on_progress=lambda c, t: self.progress.emit(c, t),
                stop=self._stop,
            )
            if not self._stop.is_set():
                self.completed.emit(n, skipped)
        except Exception as exc:
            self.failed.emit(str(exc))

    def stop(self) -> None:
        self._stop.set()
