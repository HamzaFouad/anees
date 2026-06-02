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


def _find_playlist_folder(output_root: str, prefix: str) -> str | None:
    """Scan output_root for the first directory whose name starts with '{prefix}_'.

    Scanning by prefix rather than reconstructing the exact name avoids mismatches
    when the on-disk folder was sanitized differently from the in-memory title.
    """
    try:
        for entry in os.scandir(output_root):
            if entry.is_dir() and entry.name.startswith(f"{prefix}_"):
                return entry.path
    except OSError:
        pass
    return None


@dataclass
class _Entry:
    src: str
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
        splitter_paths: list[str] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        stop: threading.Event | None = None,
        csv_dir: str | None = None,
    ) -> int:
        """Move MP3s from each playlist folder into *dest_path*, renamed
        sequentially starting from JOC_BASE (1111.mp3, 1112.mp3, …).

        *splitter_paths* is a list of local MP3 paths — one per playlist.
        Each splitter is inserted BEFORE its corresponding playlist, giving
        N splitters for N playlists:
            spl_1 → PL1 → spl_2 → PL2 → … → spl_N → PLN

        A CSV summary is written next to *dest_path*.
        Returns total files moved/copied.
        """
        if stop is None:
            stop = threading.Event()
        if on_progress is None:
            on_progress = lambda *_: None

        try:
            Path(dest_path).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            msg = f"Cannot create destination folder: {exc}"
            self._on_log(msg)
            raise RuntimeError(msg) from exc

        ordered = sorted(playlists, key=lambda p: p.prefix)

        entries: list[_Entry] = []
        skipped: list[str] = []
        found_count = 0
        for pl in ordered:
            folder = _find_playlist_folder(output_root, pl.prefix)
            if folder is None:
                msg = f"folder not found for prefix {pl.prefix!r} — skipped from merge"
                self._on_log(msg)
                skipped.append(pl.title or pl.prefix)
                continue
            mp3s = sorted(f for f in os.listdir(folder) if f.lower().endswith(".mp3"))
            if not mp3s:
                msg = f"no MP3s in {folder} — folder may have been partially merged already"
                self._on_log(msg)
                skipped.append(pl.title or pl.prefix)
                continue

            # insert splitter before this playlist — use found_count, not enumerate idx,
            # so skipped playlists don't shift the splitter assignment
            if splitter_paths and found_count < len(splitter_paths):
                entries.append(_Entry(
                    splitter_paths[found_count], is_splitter=True, playlist_name="splitter"
                ))

            for fname in mp3s:
                entries.append(_Entry(
                    os.path.join(folder, fname),
                    is_splitter=False,
                    playlist_name=pl.title,
                ))
            found_count += 1

        if skipped:
            self._on_log(f"WARNING: {len(skipped)} playlist(s) skipped: {', '.join(skipped)}")

        total = len(entries)
        moved = 0

        for seq, entry in enumerate(entries):
            if stop.is_set():
                self._on_log("Merge stopped by user")
                break
            joc = JOC_BASE + seq
            dest_file = os.path.join(dest_path, f"{joc}.mp3")
            try:
                if entry.is_splitter:
                    shutil.copy2(entry.src, dest_file)
                else:
                    shutil.move(entry.src, dest_file)
                moved += 1
                self._on_log(f"→ {joc}.mp3")
            except OSError as exc:
                self._on_log(f"failed {joc}.mp3: {exc}")
            on_progress(moved, total)

        if moved > 0:
            out_dir = csv_dir or str(Path(dest_path).parent)
            self._write_summary_csv(entries, out_dir)
            self._write_detail_csv(entries, out_dir)

        self._on_log(f"Merge complete — {moved}/{total} files in {dest_path}")
        return moved, skipped

    def _write_summary_csv(self, entries: list[_Entry], csv_dir: str) -> None:
        csv_path = os.path.join(csv_dir, "summary.csv")
        rows = []
        i = 0
        while i < len(entries):
            name = entries[i].playlist_name
            j = i
            while j < len(entries) and entries[j].playlist_name == name:
                j += 1
            rows.append({
                "playlist_name": name,
                "start":         i + 1,
                "end":           j,
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
            self._on_log(f"Summary CSV failed: {exc}")

    def _write_detail_csv(self, entries: list[_Entry], csv_dir: str) -> None:
        """One row per file: joc_number, original_filename, playlist_name."""
        csv_path = os.path.join(csv_dir, "detail.csv")
        rows = [
            {
                "joc_number":       JOC_BASE + seq,
                "original_filename": os.path.basename(e.src) if not e.is_splitter else "splitter",
                "playlist_name":    e.playlist_name,
            }
            for seq, e in enumerate(entries)
        ]
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["joc_number", "original_filename", "playlist_name"])
                w.writeheader()
                w.writerows(rows)
            self._on_log(f"Detail CSV: {csv_path}")
        except OSError as exc:
            self._on_log(f"Detail CSV failed: {exc}")
