from __future__ import annotations
from PySide6.QtCore import QThread, Signal


class InfoWorker(QThread):
    """Fetches playlist metadata (title + video list) without downloading."""
    info_ready   = Signal(str, object, str)   # playlist_id, list[Video], real_title
    fetch_failed = Signal(str, str)           # playlist_id, error_message

    def __init__(self, playlist_id: str, url: str, parent=None):
        super().__init__(parent)
        self._playlist_id = playlist_id
        self._url         = url

    def run(self) -> None:
        from backend.api import InfoAPI
        try:
            videos, title = InfoAPI().fetch_playlist(self._url)
        except Exception as exc:
            self.fetch_failed.emit(self._playlist_id, str(exc))
            return
        if videos:
            self.info_ready.emit(self._playlist_id, videos, title)
        else:
            self.fetch_failed.emit(self._playlist_id, "No videos found — check the URL")
