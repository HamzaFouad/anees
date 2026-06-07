"""Run orchestration extracted from AppState.

This controller owns worker lifecycle (start/pause/resume/stop/retry/info-fetch)
while AppState remains the single state holder and signal source.
"""
from __future__ import annotations

from typing import Any, Callable


class RunController:
    def __init__(
        self,
        *,
        make_download_worker: Callable[[list, str], Any],
        make_retry_worker: Callable[[Any, list[int], str], Any],
        make_info_worker: Callable[[str, str], Any],
        on_videos_ready: Callable[[str, object, str], None],
        on_video_stage: Callable[[str, int, str, float], None],
        on_video_meta: Callable[[str, int, str, int], None],
        on_log: Callable[[str, str, str], None],
        on_run_complete: Callable[[], None],
        on_retry_complete: Callable[[], None],
    ) -> None:
        self._make_download_worker = make_download_worker
        self._make_retry_worker = make_retry_worker
        self._make_info_worker = make_info_worker

        self._on_videos_ready = on_videos_ready
        self._on_video_stage = on_video_stage
        self._on_video_meta = on_video_meta
        self._on_log = on_log
        self._on_run_complete = on_run_complete
        self._on_retry_complete = on_retry_complete

        self._download_worker: Any | None = None
        self._retry_workers: set[Any] = set()
        self._info_workers: set[Any] = set()

    def start_run(self, playlists: list, output_root: str) -> bool:
        pending = [p for p in playlists if p.status != "done"]
        if not pending:
            return False

        worker = self._make_download_worker(pending, output_root)
        worker.videos_ready.connect(self._on_videos_ready)
        worker.video_stage.connect(self._on_video_stage)
        worker.video_meta.connect(self._on_video_meta)
        worker.log_added.connect(self._on_log)

        def _on_complete() -> None:
            self._download_worker = None
            self._on_run_complete()

        worker.run_complete.connect(_on_complete)
        worker.start()
        self._download_worker = worker
        return True

    def pause_run(self) -> None:
        if self._download_worker:
            self._download_worker.pause()

    def resume_run(self) -> None:
        if self._download_worker:
            self._download_worker.resume()

    def stop_run(self, wait_ms: int = 3000) -> None:
        if self._download_worker:
            self._download_worker.stop()
            self._download_worker.wait(wait_ms)
            self._download_worker = None

    def retry_videos(self, playlist: Any, video_indices: list[int], output_root: str) -> None:
        if not video_indices:
            return
        worker = self._make_retry_worker(playlist, video_indices, output_root)
        self._retry_workers.add(worker)

        worker.video_stage.connect(self._on_video_stage)
        worker.video_meta.connect(self._on_video_meta)
        worker.log_added.connect(self._on_log)

        def _cleanup() -> None:
            self._retry_workers.discard(worker)
            worker.deleteLater()
            self._on_retry_complete()

        worker.completed.connect(_cleanup)
        worker.start()

    def fetch_info_async(self, playlist_id: str, url: str) -> None:
        worker = self._make_info_worker(playlist_id, url)
        self._info_workers.add(worker)

        worker.info_ready.connect(self._on_videos_ready)

        def _cleanup() -> None:
            self._info_workers.discard(worker)
            worker.deleteLater()

        worker.finished.connect(_cleanup)
        worker.start()
