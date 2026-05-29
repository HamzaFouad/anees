from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from backend.models import Video


class InfoWorker(QThread):
    """Fetches playlist metadata (title + video list) without downloading."""
    info_ready = Signal(str, object, str)   # playlist_id, list[Video], real_title

    def __init__(self, playlist_id: str, url: str, parent=None):
        super().__init__(parent)
        self._playlist_id = playlist_id
        self._url         = url

    def run(self) -> None:
        import yt_dlp
        from backend.commands.ytdlp import make_info_opts
        videos: list[Video] = []
        title = ""
        try:
            with yt_dlp.YoutubeDL(make_info_opts()) as ydl:
                info = ydl.extract_info(self._url, download=False)
                title = info.get("title") or ""
                for entry in (info.get("entries") or []):
                    if entry:
                        videos.append(Video(
                            title        = entry.get("title") or f"Video {len(videos)+1}",
                            duration_sec = int(entry.get("duration") or 0),
                            stage        = "queued",
                        ))
        except Exception as exc:
            print(f"[InfoWorker] {exc}", flush=True)

        if videos:
            self.info_ready.emit(self._playlist_id, videos, title)
