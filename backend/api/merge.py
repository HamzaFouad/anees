from __future__ import annotations
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable

from backend.models import Playlist


class MergeAPI:
    def fetch_splitter_playlist(self, playlist_url: str) -> list[tuple[str, str, int]]:
        """Return [(video_url, title, duration_sec)] for all videos in a playlist."""
        from backend.services.splitter_service import SplitterService
        return SplitterService().fetch_playlist_videos(playlist_url)

    def merge(
        self,
        playlists: list[Playlist],
        output_root: str,
        dest_path: str,
        splitter_urls: list[str] | None = None,
        on_log: Callable[[str], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        stop: threading.Event | None = None,
    ) -> int:
        """Build a dated memory-card folder structure inside *dest_path*:

            memory_card_DD_MM_YYYY/
              ├── _splitter_tmp_N/      ← downloaded splitter clips
              ├── memory_card_..._summary.csv
              ├── memory_card_..._detail.csv
              └── memory_audios/        ← the sequentially numbered MP3s
        """
        from backend.services.merge_service import MergeService
        from backend.services.splitter_service import SplitterService

        if stop is None:
            stop = threading.Event()
        log = on_log or (lambda _: None)

        now = datetime.now()
        card_name = f"memory_card_{now.day:02d}_{now.month:02d}_{now.year}"
        card_root = os.path.join(dest_path, card_name)
        audio_dest = os.path.join(card_root, "memory_audios")
        Path(audio_dest).mkdir(parents=True, exist_ok=True)

        splitter_paths: list[str] | None = None
        if splitter_urls and not stop.is_set():
            splitter_paths = []
            for i, url in enumerate(splitter_urls):
                tmp_dir = os.path.join(card_root, f"_splitter_tmp_{i}")
                log(f"Downloading splitter {i + 1}/{len(splitter_urls)}…")
                try:
                    path = SplitterService().download_clip(url, tmp_dir, stop)
                    splitter_paths.append(path)
                except Exception as exc:
                    log(f"Splitter {i + 1} download failed: {exc} — skipping")

        return MergeService(on_log=log).merge(
            playlists, output_root, audio_dest,
            splitter_paths=splitter_paths or None,
            on_progress=on_progress,
            stop=stop,
            csv_dir=card_root,
        )
