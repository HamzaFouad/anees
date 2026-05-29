from __future__ import annotations
from typing import Callable
from backend.models import Playlist, Video


class DownloadAPI:
    """Public API for playlist downloads.

    UI workers use this class — never import backend.services directly.
    """

    def __init__(
        self,
        output_root:     str | None = None,
        on_videos_ready: Callable[[str, list[Video]], None] | None = None,
        on_video_stage:  Callable[[str, int, str, float], None] | None = None,
        on_video_meta:   Callable[[str, int, str, int], None] | None = None,
        on_log:          Callable[[str, str, str], None] | None = None,
        on_complete:     Callable[[], None] | None = None,
    ):
        from backend.services.download_service import DownloadService
        self._svc = DownloadService(
            output_root     = output_root,
            on_videos_ready = on_videos_ready,
            on_video_stage  = on_video_stage,
            on_video_meta   = on_video_meta,
            on_log          = on_log,
            on_complete     = on_complete,
        )

    def execute(self, playlists: list[Playlist]) -> None:
        self._svc.execute(playlists)

    def stop(self)   -> None: self._svc.stop()
    def pause(self)  -> None: self._svc.pause()
    def resume(self) -> None: self._svc.resume()
