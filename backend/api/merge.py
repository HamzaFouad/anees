from __future__ import annotations
import os
import threading
from typing import Callable

from backend.models import Playlist


class MergeAPI:
    def fetch_splitter_info(self, url: str) -> tuple[str, int]:
        """Return (title, duration_sec) for a YouTube video URL."""
        from backend.services.splitter_service import SplitterService
        return SplitterService().fetch_info(url)

    def merge(
        self,
        playlists: list[Playlist],
        output_root: str,
        dest_path: str,
        splitter_url: str | None = None,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        stop: threading.Event | None = None,
    ) -> int:
        """Merge selected playlists into *dest_path*.

        If *splitter_url* is given the clip is downloaded first and inserted
        between each playlist in the output.
        Returns total files copied.
        """
        from backend.services.merge_service import MergeService
        from backend.services.splitter_service import SplitterService

        if stop is None:
            stop = threading.Event()
        log = on_log or (lambda _: None)

        splitter_path: str | None = None
        if splitter_url and not stop.is_set():
            tmp_dir = os.path.join(dest_path, "_splitter_tmp")
            log("Downloading splitter clip…")
            try:
                splitter_path = SplitterService().download_clip(splitter_url, tmp_dir, stop)
                log(f"Splitter ready: {os.path.basename(splitter_path)}")
            except Exception as exc:
                log(f"Splitter download failed: {exc} — continuing without splitter")
                splitter_path = None

        return MergeService(on_log=log).merge(
            playlists, output_root, dest_path,
            splitter_path=splitter_path,
            on_progress=on_progress,
            stop=stop,
        )
