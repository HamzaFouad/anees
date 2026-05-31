from __future__ import annotations
import csv
import os
import re
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from backend.models import Playlist

JOC_BASE = 1111  # first JOC number assigned to the first merged file


def _safe_name(s: str, maxlen: int = 60) -> str:
    return re.sub(r'[^\w\s-]', '_', s).strip('_ ')[:maxlen].strip()


def _playlist_folder(pl: Playlist) -> str:
    return f"{pl.prefix}_{_safe_name(pl.title)}"


@dataclass
class _Entry:
    src: str          # source path (None = splitter copy)
    is_splitter: bool
    playlist_name: str


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
        """Move MP3s from each playlist folder into *dest_path*, renamed
        sequentially starting from JOC_BASE (1111.mp3, 1112.mp3, …).

        A CSV summary is written next to *dest_path* with one row per
        playlist showing its start/end positions and JOC numbers.

        Returns the total number of files moved.
        """
        if stop is None:
            stop = threading.Event()
        if on_progress is None:
            on_progress = lambda *_: None

        Path(dest_path).mkdir(parents=True, exist_ok=True)

        ordered = sorted(playlists, key=lambda p: p.prefix)

        # Build flat entry list in final order
        entries: list[_Entry] = []
        for idx, pl in enumerate(ordered):
            folder = os.path.join(output_root, _playlist_folder(pl))
            if not os.path.isdir(folder):
                self._on_log(f"folder not found, skipping: {folder}")
                continue
            mp3s = sorted(f for f in os.listdir(folder) if f.lower().endswith(".mp3"))
            if not mp3s:
                continue
            if splitter_path and idx > 0:
                entries.append(_Entry(splitter_path, is_splitter=True, playlist_name="splitter"))
            for fname in mp3s:
                entries.append(_Entry(
                    os.path.join(folder, fname),
                    is_splitter=False,
                    playlist_name=pl.title,
                ))

        total = len(entries)

        # Move / copy files with sequential JOC names
        moved = 0
        for seq, entry in enumerate(entries):
            if stop.is_set():
                self._on_log("Merge stopped by user")
                break
            joc = JOC_BASE + seq
            dest_file = os.path.join(dest_path, f"{joc}.mp3")
            try:
                if entry.is_splitter:
                    # splitter is reused across insertions — copy, not move
                    shutil.copy2(entry.src, dest_file)
                else:
                    shutil.move(entry.src, dest_file)
                moved += 1
                self._on_log(f"→ {joc}.mp3")
            except OSError as exc:
                self._on_log(f"failed {joc}.mp3: {exc}")
            on_progress(moved, total)

        # Write CSV summary (outside dest_path)
        if moved > 0:
            self._write_csv(entries, dest_path)

        self._on_log(f"Merge complete — {moved}/{total} files in {dest_path}")
        return moved

    def _write_csv(self, entries: list[_Entry], dest_path: str) -> None:
        csv_path = os.path.join(
            str(Path(dest_path).parent),
            f"{Path(dest_path).name}_summary.csv",
        )
        # Group consecutive entries by playlist_name
        rows = []
        i = 0
        while i < len(entries):
            name = entries[i].playlist_name
            start_seq = i + 1          # 1-based
            j = i
            while j < len(entries) and entries[j].playlist_name == name:
                j += 1
            end_seq = j                # last index (1-based)
            rows.append({
                "playlist_name": name,
                "start":         start_seq,
                "end":           end_seq,
                "joc_start":     JOC_BASE + i,
                "joc_end":       JOC_BASE + j - 1,
            })
            i = j

        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["playlist_name", "start", "end", "joc_start", "joc_end"])
                w.writeheader()
                w.writerows(rows)
            self._on_log(f"Summary CSV: {csv_path}")
        except OSError as exc:
            self._on_log(f"CSV write failed: {exc}")
