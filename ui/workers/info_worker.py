from __future__ import annotations
from PySide6.QtCore import QThread, Signal
class InfoWorker(QThread):
    """Fetches playlist metadata (title + video list) without downloading."""
    info_ready = Signal(str, object, str)   # playlist_id, list[Video], real_title

    def __init__(self, playlist_id: str, url: str, parent=None):
        super().__init__(parent)
        self._playlist_id = playlist_id
        self._url         = url

    def run(self) -> None:
        from backend.commands.ytdlp import YtdlpClient
        try:
            videos, title = YtdlpClient().fetch_info(self._url)
        except Exception as exc:
            print(f"[InfoWorker] {exc}", flush=True)
            return
        if videos:
            self.info_ready.emit(self._playlist_id, videos, title)
