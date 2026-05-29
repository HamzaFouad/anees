from __future__ import annotations
from PySide6.QtCore import QThread, Signal
from backend.models import Playlist, Video
from backend.services.download_service import DownloadService


class DownloadWorker(QThread):
    videos_ready = Signal(str, object, str)         # playlist_id, list[Video], real_title
    video_stage  = Signal(str, int, str, float)     # playlist_id, idx, stage, progress
    video_meta   = Signal(str, int, str, int)        # playlist_id, idx, title, duration_sec
    log_added    = Signal(str, str, str)             # level, src, msg
    run_complete = Signal()

    def __init__(self, playlists: list[Playlist], output_root: str, parent=None):
        super().__init__(parent)
        self._playlists = playlists
        self._service   = DownloadService(
            output_root     = output_root,
            on_videos_ready = self.videos_ready.emit,
            on_video_stage  = self.video_stage.emit,
            on_video_meta   = self.video_meta.emit,
            on_log          = self.log_added.emit,
            on_complete     = self.run_complete.emit,
        )

    def run(self) -> None:
        try:
            self._service.execute(self._playlists)
        except Exception as exc:
            import traceback
            print(f"[DownloadWorker] UNCAUGHT: {exc}", flush=True)
            traceback.print_exc()
            self.log_added.emit("error", "worker", str(exc))
    def stop(self)   -> None: self._service.stop()
    def pause(self)  -> None: self._service.pause()
    def resume(self) -> None: self._service.resume()
