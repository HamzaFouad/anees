"""Tests for DownloadService._scan_existing and resume behaviour in _run_playlist."""
from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, patch, call

import pytest

from backend.services.download_service import DownloadService
from backend.types import VideoStage
from tests.conftest import make_playlist, make_video


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_service(tmp_path, stage_cb=None, log_cb=None):
    """Return a DownloadService wired to tmp_path with controllable callbacks."""
    return DownloadService(
        output_root=str(tmp_path),
        on_video_stage=stage_cb or (lambda *_: None),
        on_log=log_cb or (lambda *_: None),
    )


def _pl(tmp_path, prefix="00", title="My Playlist", n_videos=3):
    videos = [make_video(title=f"Vid {i+1}") for i in range(n_videos)]
    pl = make_playlist(prefix=prefix, title=title, videos=videos)
    pl.video_count = n_videos
    return pl


def _touch(folder, name):
    """Create an empty file at folder/name."""
    os.makedirs(folder, exist_ok=True)
    open(os.path.join(folder, name), "w").close()


# ── _scan_existing ────────────────────────────────────────────────────────────

class TestScanExisting:

    def test_returns_all_when_folder_absent(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=3)
        assert svc._scan_existing(pl) == [1, 2, 3]

    def test_returns_all_when_folder_empty(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=3)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        os.makedirs(folder)
        assert svc._scan_existing(pl) == [1, 2, 3]

    def test_last_file_always_repending(self, tmp_path):
        """The highest-index file found is always re-queued (may be incomplete)."""
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=3)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Vid 1.mp3")
        _touch(folder, "02_Vid 2.mp3")
        _touch(folder, "03_Vid 3.mp3")
        pending = svc._scan_existing(pl)
        # video 3 is the last found → deleted and re-queued
        assert 3 in pending
        assert 1 not in pending
        assert 2 not in pending

    def test_last_file_deleted_from_disk(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=3)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Vid 1.mp3")
        _touch(folder, "02_Vid 2.mp3")
        _touch(folder, "03_Vid 3.mp3")
        svc._scan_existing(pl)
        assert not os.path.exists(os.path.join(folder, "03_Vid 3.mp3"))
        assert os.path.exists(os.path.join(folder, "01_Vid 1.mp3"))
        assert os.path.exists(os.path.join(folder, "02_Vid 2.mp3"))

    def test_returns_pending_subset(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=4)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Vid 1.mp3")
        _touch(folder, "03_Vid 3.mp3")
        # video 3 is last found → deleted and re-queued; video 2 and 4 were already missing
        pending = svc._scan_existing(pl)
        assert 2 in pending
        assert 3 in pending
        assert 4 in pending
        assert 1 not in pending

    def test_marks_found_videos_as_done(self, tmp_path):
        stages = []
        svc = _make_service(tmp_path, stage_cb=lambda pid, idx, stage, prog: stages.append((idx, stage)))
        pl = _pl(tmp_path, n_videos=3)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Vid 1.mp3")
        _touch(folder, "02_Vid 2.mp3")
        _touch(folder, "03_Vid 3.mp3")
        svc._scan_existing(pl)
        # videos 1 and 2 confirmed done; video 3 (last) deleted and not marked done
        assert (0, VideoStage.DONE) in stages
        assert (1, VideoStage.DONE) in stages
        assert (2, VideoStage.DONE) not in stages

    def test_ignores_spd_temp_files(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=2)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        # Only a crash-temp exists for video 1 — should NOT count as done
        _touch(folder, "01_Vid 1.mp3.spd.mp3")
        _touch(folder, "02_Vid 2.mp3")
        pending = svc._scan_existing(pl)
        # video 2 is the only real mp3 — it's the last found so deleted and re-queued
        # video 1 spd temp doesn't count — also pending
        assert 1 in pending
        assert 2 in pending

    def test_detects_split_parts_as_done(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=3)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        # Videos 1 and 2 have split parts; video 3 is last → deleted and re-queued
        _touch(folder, "01_Vid 1_part001.mp3")
        _touch(folder, "01_Vid 1_part002.mp3")
        _touch(folder, "02_Vid 2_part001.mp3")
        _touch(folder, "03_Vid 3.mp3")
        pending = svc._scan_existing(pl)
        assert 1 not in pending
        assert 2 not in pending
        assert 3 in pending

    def test_last_split_parts_all_deleted(self, tmp_path):
        """All parts of the last video are deleted, not just the first."""
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=2)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Vid 1.mp3")
        _touch(folder, "02_Vid 2_part001.mp3")
        _touch(folder, "02_Vid 2_part002.mp3")
        svc._scan_existing(pl)
        assert not os.path.exists(os.path.join(folder, "02_Vid 2_part001.mp3"))
        assert not os.path.exists(os.path.join(folder, "02_Vid 2_part002.mp3"))
        assert os.path.exists(os.path.join(folder, "01_Vid 1.mp3"))

    def test_handles_oserror_on_listdir(self, tmp_path):
        svc = _make_service(tmp_path)
        pl = _pl(tmp_path, n_videos=2)
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        os.makedirs(folder)
        with patch("os.listdir", side_effect=OSError("permission denied")):
            # Falls back to "all pending"
            assert svc._scan_existing(pl) == [1, 2]

    def test_prefix_check_works_for_index_above_99(self, tmp_path):
        svc = _make_service(tmp_path)
        videos = [make_video(title=f"Vid {i+1}") for i in range(102)]
        pl = make_playlist(prefix="00", title="My Playlist", videos=videos)
        pl.video_count = 102
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        # Videos 100 and 101 exist — 101 is last so deleted, 100 is confirmed done
        _touch(folder, "100_Vid 100.mp3")
        _touch(folder, "101_Vid 101.mp3")
        pending = svc._scan_existing(pl)
        assert 100 not in pending   # confirmed done
        assert 101 in pending       # last → deleted and re-queued
        assert 1 in pending         # never on disk


# ── _run_playlist resume behaviour ────────────────────────────────────────────

class TestRunPlaylistResume:

    def _make_svc_with_mock_download(self, tmp_path):
        svc = _make_service(tmp_path)
        svc._download = MagicMock()
        svc._client = MagicMock()
        svc._client.fetch_info.return_value = ([], "")
        return svc

    def test_skips_download_when_only_one_video_and_it_is_last(self, tmp_path):
        """Single-video playlist: the only file is always the last → re-downloaded."""
        svc = self._make_svc_with_mock_download(tmp_path)
        pl = _pl(tmp_path, n_videos=1)
        pl.videos = [make_video(title="Real Title 1")]
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Real Title 1.mp3")
        svc._run_playlist(pl)
        # last file deleted → pending=[1] → download called
        svc._download.assert_called_once_with(pl, playlist_items=None)

    def test_skips_download_when_all_done_except_last(self, tmp_path):
        """Videos 1..N-1 done, video N (last) deleted → only N re-downloaded."""
        svc = self._make_svc_with_mock_download(tmp_path)
        pl = _pl(tmp_path, n_videos=3)
        pl.videos = [make_video(title=f"Real Title {i+1}") for i in range(3)]
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Real Title 1.mp3")
        _touch(folder, "02_Real Title 2.mp3")
        _touch(folder, "03_Real Title 3.mp3")
        svc._run_playlist(pl)
        svc._download.assert_called_once_with(pl, playlist_items="3")

    def test_passes_playlist_items_for_partial(self, tmp_path):
        svc = self._make_svc_with_mock_download(tmp_path)
        pl = _pl(tmp_path, n_videos=4)
        pl.videos = [make_video(title=f"Real Title {i+1}") for i in range(4)]
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Real Title 1.mp3")   # video 1 confirmed done
        _touch(folder, "02_Real Title 2.mp3")   # video 2 = last found → deleted
        # videos 3 and 4 were already missing; video 2 re-queued
        svc._run_playlist(pl)
        svc._download.assert_called_once_with(pl, playlist_items="2,3,4")

    def test_passes_no_playlist_items_when_none_done(self, tmp_path):
        svc = self._make_svc_with_mock_download(tmp_path)
        pl = _pl(tmp_path, n_videos=2)
        pl.videos = [make_video(title=f"Real Title {i+1}") for i in range(2)]
        # No folder — nothing on disk
        svc._run_playlist(pl)
        svc._download.assert_called_once_with(pl, playlist_items=None)

    def test_logs_resume_message_on_partial(self, tmp_path):
        # 3 videos: 01 and 02 on disk; 02 is last → deleted; 01 confirmed done
        # → already=1, pending=[2,3] → "Resuming" fires
        logs = []
        svc = _make_service(tmp_path, log_cb=lambda lvl, src, msg: logs.append(msg))
        svc._download = MagicMock()
        svc._client = MagicMock()
        pl = _pl(tmp_path, n_videos=3)
        pl.videos = [make_video(title=f"Real Title {i+1}") for i in range(3)]
        folder = os.path.join(str(tmp_path), "00_My Playlist")
        _touch(folder, "01_Real Title 1.mp3")
        _touch(folder, "02_Real Title 2.mp3")
        svc._run_playlist(pl)
        assert any("Resuming" in m for m in logs)
