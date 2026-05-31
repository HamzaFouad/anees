from __future__ import annotations
import os
import re
import shutil
import threading
from pathlib import Path
from typing import Callable

from backend.models import Playlist


def _safe_name(s: str, maxlen: int = 60) -> str:
    return re.sub(r'[^\w\s-]', '_', s).strip('_ ')[:maxlen].strip()


def _playlist_folder(pl: Playlist) -> str:
    return f"{pl.prefix}_{_safe_name(pl.title)}"


class MergeService:
    def __init__(self, on_log: Callable[[str], None] | None = None):
        self._on_log = on_log or (lambda _: None)

    def merge(
        self,
        playlists: list[Playlist],
        output_root: str,
        dest_path: str,
        splitter_path: str | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        stop: threading.Event | None = None,
    ) -> int:
        """Copy MP3s from each playlist folder into *dest_path*.

        Files are renamed ``{pl.prefix}_{original_filename}``.
        If *splitter_path* is given a copy is inserted between each playlist.
        Returns the total number of files written.
        """
        if stop is None:
            stop = threading.Event()
        if on_progress is None:
            on_progress = lambda *_: None

        Path(dest_path).mkdir(parents=True, exist_ok=True)

        # sort by prefix to keep playlist order
        ordered = sorted(playlists, key=lambda p: p.prefix)

        # pre-count total for progress
        total = 0
        file_map: list[tuple[str, str]] = []  # (src, dest_name)
        for idx, pl in enumerate(ordered):
            folder = os.path.join(output_root, _playlist_folder(pl))
            if not os.path.isdir(folder):
                self._on_log(f"folder not found, skipping: {folder}")
                continue
            mp3s = sorted(
                f for f in os.listdir(folder) if f.lower().endswith(".mp3")
            )
            if splitter_path and idx > 0:
                spl_name = f"{pl.prefix}_00_splitter.mp3"
                file_map.append((splitter_path, spl_name))
                total += 1
            for fname in mp3s:
                src = os.path.join(folder, fname)
                dest_name = f"{pl.prefix}_{fname}"
                file_map.append((src, dest_name))
                total += 1

        copied = 0
        for src, dest_name in file_map:
            if stop.is_set():
                self._on_log("Merge stopped by user")
                break
            dest_file = os.path.join(dest_path, dest_name)
            try:
                shutil.copy2(src, dest_file)
                copied += 1
                self._on_log(f"copied: {dest_name}")
            except OSError as exc:
                self._on_log(f"copy failed: {dest_name} — {exc}")
            on_progress(copied, total)

        self._on_log(f"Merge complete — {copied}/{total} files in {dest_path}")
        return copied
