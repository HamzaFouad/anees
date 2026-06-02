"""Tests for backend/services/merge_service.py."""
from __future__ import annotations

import os
import threading
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from backend.models import Playlist
from backend.services.merge_service import JOC_BASE, MergeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _playlist(prefix: str, title: str = "My Playlist") -> Playlist:
    return Playlist(
        id=f"id_{prefix}",
        prefix=prefix,
        title=title,
        url="https://youtube.com/playlist?list=x",
        video_count=2,
        completed=2,
        status="done",
        active_stage="",
        speed=1.0,
        split_enabled=False,
        split_min=0,
        size_mb=None,
        added_at="2026-01-01",
    )


def _folder_name(pl: Playlist) -> str:
    """Mirror _playlist_folder() from merge_service."""
    import re
    safe = re.sub(r'[^\w\s-]', '_', pl.title).strip('_ ')[:60].strip('_ ')
    return f"{pl.prefix}_{safe}"


# ---------------------------------------------------------------------------
# Test: skips missing playlist folders
# ---------------------------------------------------------------------------

class TestSkipMissingFolder:
    def test_missing_folder_is_skipped_and_returns_zero(self):
        svc = MergeService()
        pl = _playlist("A001")

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=False),
            patch("backend.services.merge_service.os.listdir"),
            patch("backend.services.merge_service.shutil.move"),
            patch("backend.services.merge_service.shutil.copy2"),
            patch("builtins.open", mock_open()),
        ):
            # mkdir must not raise
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            result = svc.merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
            )

        assert result == 0

    def test_missing_folder_logs_warning(self):
        logs = []
        svc = MergeService(on_log=logs.append)
        pl = _playlist("A001")

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=False),
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            svc.merge(playlists=[pl], output_root="/tmp/root", dest_path="/tmp/out/dest")

        assert any("skipping" in m for m in logs)


# ---------------------------------------------------------------------------
# Test: correct JOC naming
# ---------------------------------------------------------------------------

class TestJocNaming:
    def test_files_renamed_sequentially_from_joc_base(self):
        pl = _playlist("A001", "Alpha")
        folder = f"/tmp/root/{_folder_name(pl)}"
        moved_to: list[str] = []

        def fake_move(src, dst):
            moved_to.append(dst)

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["a.mp3", "b.mp3"]),
            patch("backend.services.merge_service.shutil.move", side_effect=fake_move),
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            result = MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
            )

        assert result == 2
        assert moved_to[0] == os.path.join("/tmp/out/dest", f"{JOC_BASE}.mp3")
        assert moved_to[1] == os.path.join("/tmp/out/dest", f"{JOC_BASE + 1}.mp3")

    def test_joc_base_is_1111(self):
        assert JOC_BASE == 1111


# ---------------------------------------------------------------------------
# Test: splitter insertion (N splitters for N playlists)
# ---------------------------------------------------------------------------

class TestSplitterInsertion:
    def test_splitter_inserted_before_each_playlist(self):
        pl1 = _playlist("A001", "Alpha")
        pl2 = _playlist("A002", "Beta")

        copied: list[str] = []
        moved: list[str] = []

        def fake_copy(src, dst):
            copied.append(dst)

        def fake_move(src, dst):
            moved.append(dst)

        def fake_isdir(path):
            return True

        def fake_listdir(path):
            return ["track.mp3"]

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", side_effect=fake_isdir),
            patch("backend.services.merge_service.os.listdir", side_effect=fake_listdir),
            patch("backend.services.merge_service.shutil.copy2", side_effect=fake_copy),
            patch("backend.services.merge_service.shutil.move", side_effect=fake_move),
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            result = MergeService().merge(
                playlists=[pl1, pl2],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                splitter_paths=["/spl/s1.mp3", "/spl/s2.mp3"],
            )

        # 2 splitters + 2 tracks
        assert result == 4
        # first two destinations: spl for pl1, then track for pl1
        assert len(copied) == 2
        assert len(moved) == 2
        # splitters land at JOC_BASE+0 and JOC_BASE+2
        assert copied[0] == os.path.join("/tmp/out/dest", f"{JOC_BASE}.mp3")
        assert copied[1] == os.path.join("/tmp/out/dest", f"{JOC_BASE + 2}.mp3")


# ---------------------------------------------------------------------------
# Test: stop event halts mid-merge
# ---------------------------------------------------------------------------

class TestStopEvent:
    def test_stop_halts_after_first_file(self):
        pl = _playlist("A001", "Alpha")
        stop = threading.Event()
        moved: list[str] = []

        def fake_move(src, dst):
            moved.append(dst)
            # signal stop after first move so second file is never processed
            stop.set()

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["a.mp3", "b.mp3", "c.mp3"]),
            patch("backend.services.merge_service.shutil.move", side_effect=fake_move),
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            result = MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                stop=stop,
            )

        # Only the first file completed before stop was checked
        assert result == 1
        assert len(moved) == 1

    def test_stop_already_set_moves_nothing(self):
        pl = _playlist("A001", "Alpha")
        stop = threading.Event()
        stop.set()

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["a.mp3", "b.mp3"]),
            patch("backend.services.merge_service.shutil.move") as mock_move,
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            result = MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                stop=stop,
            )

        mock_move.assert_not_called()
        assert result == 0


# ---------------------------------------------------------------------------
# Test: CSV summary written with correct rows
# ---------------------------------------------------------------------------

class TestSummaryCsv:
    def test_summary_csv_rows_match_playlists(self):
        pl1 = _playlist("A001", "Alpha")
        pl2 = _playlist("A002", "Beta")
        # first writerows call is summary, second is detail — capture separately
        summary_rows: list[dict] = []
        call_count = 0

        class FakeWriter:
            def __init__(self, *a, **kw):
                pass
            def writeheader(self):
                pass
            def writerows(self, rows):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    summary_rows.extend(rows)

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["t.mp3"]),
            patch("backend.services.merge_service.shutil.move"),
            patch("builtins.open", mock_open()),
            patch("backend.services.merge_service.csv.DictWriter", FakeWriter),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            MergeService().merge(
                playlists=[pl1, pl2],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                csv_dir="/tmp/csv",
            )

        playlist_names = [r["playlist_name"] for r in summary_rows]
        assert "Alpha" in playlist_names
        assert "Beta" in playlist_names
        for row in summary_rows:
            assert "joc_start" in row
            assert "joc_end" in row
            assert row["joc_start"] >= JOC_BASE


# ---------------------------------------------------------------------------
# Test: CSV detail written with joc_number, original_filename, playlist_name
# ---------------------------------------------------------------------------

class TestDetailCsv:
    def test_detail_csv_has_correct_fields(self):
        pl = _playlist("A001", "Alpha")
        detail_rows: list[dict] = []

        call_count = 0

        class FakeWriter:
            def __init__(self, f, fieldnames, **kw):
                self._fields = fieldnames

            def writeheader(self):
                pass

            def writerows(self, rows):
                nonlocal call_count
                call_count += 1
                # second call is detail CSV
                if call_count == 2:
                    detail_rows.extend(rows)

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["song.mp3"]),
            patch("backend.services.merge_service.shutil.move"),
            patch("builtins.open", mock_open()),
            patch("backend.services.merge_service.csv.DictWriter", FakeWriter),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                csv_dir="/tmp/csv",
            )

        assert len(detail_rows) == 1
        row = detail_rows[0]
        assert row["joc_number"] == JOC_BASE
        assert row["original_filename"] == "song.mp3"
        assert row["playlist_name"] == "Alpha"

    def test_detail_csv_splitter_rows_named_splitter(self):
        pl = _playlist("A001", "Alpha")
        detail_rows: list[dict] = []
        call_count = 0

        class FakeWriter:
            def __init__(self, f, fieldnames, **kw):
                pass

            def writeheader(self):
                pass

            def writerows(self, rows):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    detail_rows.extend(rows)

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["track.mp3"]),
            patch("backend.services.merge_service.shutil.move"),
            patch("backend.services.merge_service.shutil.copy2"),
            patch("builtins.open", mock_open()),
            patch("backend.services.merge_service.csv.DictWriter", FakeWriter),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                splitter_paths=["/spl/intro.mp3"],
                csv_dir="/tmp/csv",
            )

        assert len(detail_rows) == 2
        splitter_row = detail_rows[0]
        assert splitter_row["original_filename"] == "splitter"
        assert splitter_row["playlist_name"] == "splitter"


# ---------------------------------------------------------------------------
# Test: mkdir failure raises RuntimeError
# ---------------------------------------------------------------------------

class TestMkdirFailure:
    def test_raises_runtime_error_on_mkdir_failure(self):
        svc = MergeService()
        pl = _playlist("A001")

        with patch("backend.services.merge_service.Path") as MockPath:
            MockPath.return_value.mkdir.side_effect = OSError("permission denied")

            with pytest.raises(RuntimeError, match="Cannot create destination folder"):
                svc.merge(
                    playlists=[pl],
                    output_root="/tmp/root",
                    dest_path="/tmp/out/dest",
                )

    def test_mkdir_failure_logs_message(self):
        logs = []
        svc = MergeService(on_log=logs.append)

        with patch("backend.services.merge_service.Path") as MockPath:
            MockPath.return_value.mkdir.side_effect = OSError("no space left")

            with pytest.raises(RuntimeError):
                svc.merge(
                    playlists=[],
                    output_root="/tmp/root",
                    dest_path="/tmp/out/dest",
                )

        assert any("Cannot create destination folder" in m for m in logs)


# ---------------------------------------------------------------------------
# Test: progress callback fired for each file
# ---------------------------------------------------------------------------

class TestProgressCallback:
    def test_progress_called_once_per_file(self):
        pl = _playlist("A001", "Alpha")
        progress_calls: list[tuple[int, int]] = []

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["a.mp3", "b.mp3", "c.mp3"]),
            patch("backend.services.merge_service.shutil.move"),
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                on_progress=lambda done, total: progress_calls.append((done, total)),
            )

        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)

    def test_on_progress_total_counts_splitters(self):
        pl = _playlist("A001", "Alpha")
        totals: list[int] = []

        with (
            patch("backend.services.merge_service.Path") as MockPath,
            patch("backend.services.merge_service.os.path.isdir", return_value=True),
            patch("backend.services.merge_service.os.listdir", return_value=["a.mp3"]),
            patch("backend.services.merge_service.shutil.move"),
            patch("backend.services.merge_service.shutil.copy2"),
            patch("builtins.open", mock_open()),
        ):
            MockPath.return_value.mkdir.return_value = None
            MockPath.return_value.parent = Path("/tmp/out")

            MergeService().merge(
                playlists=[pl],
                output_root="/tmp/root",
                dest_path="/tmp/out/dest",
                splitter_paths=["/spl/s.mp3"],
                on_progress=lambda done, total: totals.append(total),
            )

        # 1 splitter + 1 track = total 2
        assert all(t == 2 for t in totals)
        assert len(totals) == 2
