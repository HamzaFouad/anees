"""Tests for backend/models.py — dataclasses, enums, defaults, and transitions."""
from __future__ import annotations

import pytest

from backend.models import (
    HistoryPlaylist,
    HistoryRun,
    LogEntry,
    Playlist,
    RunState,
    Video,
)
from tests.conftest import make_playlist, make_video


# ---------------------------------------------------------------------------
# RunState
# ---------------------------------------------------------------------------

class TestRunState:
    def test_values(self):
        assert RunState.IDLE.value == "idle"
        assert RunState.RUNNING.value == "running"
        assert RunState.PAUSED.value == "paused"
        assert RunState.COMPLETE.value == "complete"

    def test_enum_members(self):
        members = {m.value for m in RunState}
        assert members == {"idle", "running", "paused", "complete"}

    def test_lookup_by_value(self):
        assert RunState("running") is RunState.RUNNING

    def test_identity(self):
        assert RunState.IDLE is not RunState.RUNNING
        assert RunState.PAUSED is not RunState.COMPLETE


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------

class TestVideoDefaults:
    def test_required_fields_stored(self):
        v = Video(title="My Video", duration_sec=300, stage="queued")
        assert v.title == "My Video"
        assert v.duration_sec == 300
        assert v.stage == "queued"

    def test_default_progress(self):
        v = Video(title="x", duration_sec=60, stage="queued")
        assert v.progress == 0.0

    def test_default_failed_at_is_none(self):
        v = Video(title="x", duration_sec=60, stage="queued")
        assert v.failed_at is None

    def test_default_error_is_none(self):
        v = Video(title="x", duration_sec=60, stage="queued")
        assert v.error is None

    def test_default_retry_count(self):
        v = Video(title="x", duration_sec=60, stage="queued")
        assert v.retry_count == 0


class TestVideoStageTransitions:
    VALID_STAGES = ["queued", "download", "mp3", "speed", "split", "done", "failed"]

    @pytest.mark.parametrize("stage", VALID_STAGES)
    def test_stage_stored_correctly(self, stage):
        v = Video(title="x", duration_sec=10, stage=stage)
        assert v.stage == stage

    def test_progress_updated(self):
        v = Video(title="x", duration_sec=10, stage="download", progress=0.5)
        assert v.progress == 0.5

    def test_failed_state_with_error(self):
        v = Video(title="x", duration_sec=10, stage="failed",
                  failed_at="download", error="HTTP 403")
        assert v.stage == "failed"
        assert v.failed_at == "download"
        assert v.error == "HTTP 403"

    def test_retry_count_incremented(self):
        v = Video(title="x", duration_sec=10, stage="queued", retry_count=2)
        assert v.retry_count == 2

    def test_done_stage_no_error(self):
        v = Video(title="x", duration_sec=10, stage="done", progress=1.0)
        assert v.stage == "done"
        assert v.error is None
        assert v.failed_at is None


class TestVideoMutability:
    def test_stage_can_be_reassigned(self):
        v = Video(title="x", duration_sec=10, stage="queued")
        v.stage = "download"
        assert v.stage == "download"

    def test_progress_can_be_updated(self):
        v = Video(title="x", duration_sec=10, stage="download", progress=0.0)
        v.progress = 0.75
        assert v.progress == 0.75

    def test_retry_count_can_be_incremented(self):
        v = Video(title="x", duration_sec=10, stage="queued", retry_count=0)
        v.retry_count += 1
        assert v.retry_count == 1


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

class TestPlaylistDefaults:
    def test_videos_default_to_empty_list(self):
        p = Playlist(
            id="p1",
            prefix="P01",
            title="My Playlist",
            url="https://youtube.com/playlist?list=X",
            video_count=0,
            completed=0,
            status="queued",
            active_stage="queued",
            speed=1.0,
            split_enabled=False,
            split_min=30,
            size_mb=None,
            added_at="2026-06-01T00:00:00",
        )
        assert p.videos == []
        assert isinstance(p.videos, list)

    def test_videos_list_is_not_shared_between_instances(self):
        p1 = Playlist(
            id="p1", prefix="P01", title="A", url="u", video_count=0,
            completed=0, status="queued", active_stage="queued", speed=1.0,
            split_enabled=False, split_min=30, size_mb=None,
            added_at="2026-06-01T00:00:00",
        )
        p2 = Playlist(
            id="p2", prefix="P02", title="B", url="u", video_count=0,
            completed=0, status="queued", active_stage="queued", speed=1.0,
            split_enabled=False, split_min=30, size_mb=None,
            added_at="2026-06-01T00:00:00",
        )
        p1.videos.append(make_video())
        assert len(p2.videos) == 0

    def test_size_mb_can_be_none(self):
        p = make_playlist()
        assert p.size_mb is None

    def test_size_mb_can_be_float(self):
        p = make_playlist()
        p.size_mb = 42.5
        assert p.size_mb == 42.5


class TestPlaylistStatusValues:
    @pytest.mark.parametrize("status", ["queued", "active", "done"])
    def test_valid_status(self, status):
        p = make_playlist()
        p.status = status
        assert p.status == status

    def test_initial_status_from_helper(self):
        p = make_playlist()
        assert p.status == "queued"


class TestPlaylistVideoList:
    def test_videos_stored_correctly(self):
        videos = [make_video(title=f"V{i}") for i in range(3)]
        p = make_playlist(videos=videos)
        assert len(p.videos) == 3
        assert p.videos[0].title == "V0"

    def test_video_count_reflects_list_length(self):
        videos = [make_video() for _ in range(5)]
        p = make_playlist(videos=videos)
        assert p.video_count == 5

    def test_completed_count_uses_done_stage(self):
        videos = [
            make_video(stage="done"),
            make_video(stage="done"),
            make_video(stage="queued"),
        ]
        p = make_playlist(videos=videos)
        assert p.completed == 2

    def test_appending_video_changes_list(self):
        p = make_playlist()
        p.videos.append(make_video(title="Late Video"))
        assert len(p.videos) == 1
        assert p.videos[0].title == "Late Video"


# ---------------------------------------------------------------------------
# HistoryRun
# ---------------------------------------------------------------------------

class TestHistoryRunDefaults:
    def test_playlists_default_to_empty_list(self):
        run = HistoryRun(
            id="run-1",
            num=1,
            started_at="2026-06-01T10:00:00",
            duration_min=5,
            playlist_count=0,
            video_count=0,
            size_mb=0.0,
            output_path="/tmp/output",
            merged=False,
            merged_path=None,
            status="success",
        )
        assert run.playlists == []
        assert isinstance(run.playlists, list)

    def test_merged_path_can_be_none(self):
        run = HistoryRun(
            id="run-1", num=1, started_at="2026-06-01T10:00:00",
            duration_min=5, playlist_count=1, video_count=3,
            size_mb=10.0, output_path="/tmp/out", merged=False,
            merged_path=None, status="success",
        )
        assert run.merged_path is None

    def test_merged_path_can_be_set(self):
        run = HistoryRun(
            id="run-1", num=1, started_at="2026-06-01T10:00:00",
            duration_min=5, playlist_count=1, video_count=3,
            size_mb=10.0, output_path="/tmp/out", merged=True,
            merged_path="/tmp/merged.mp3", status="success",
        )
        assert run.merged_path == "/tmp/merged.mp3"

    def test_status_values(self):
        for status in ("success", "partial"):
            run = HistoryRun(
                id="r", num=1, started_at="t", duration_min=1,
                playlist_count=1, video_count=1, size_mb=1.0,
                output_path="/o", merged=False, merged_path=None,
                status=status,
            )
            assert run.status == status

    def test_playlists_list_not_shared(self):
        def _make_run(run_id):
            return HistoryRun(
                id=run_id, num=1, started_at="t", duration_min=1,
                playlist_count=0, video_count=0, size_mb=0.0,
                output_path="/o", merged=False, merged_path=None,
                status="success",
            )
        r1 = _make_run("r1")
        r2 = _make_run("r2")
        r1.playlists.append(
            HistoryPlaylist(prefix="P01", title="A", videos=1, size_mb=5.0, speed=1.0)
        )
        assert len(r2.playlists) == 0


class TestHistoryRunFields:
    def test_all_fields_stored(self):
        hp = HistoryPlaylist(prefix="P01", title="My PL", videos=10, size_mb=50.0, speed=1.5)
        run = HistoryRun(
            id="abc-123",
            num=7,
            started_at="2026-06-01T08:30:00",
            duration_min=12,
            playlist_count=1,
            video_count=10,
            size_mb=50.0,
            output_path="/home/user/anees",
            merged=True,
            merged_path="/home/user/anees/merged.mp3",
            status="success",
            playlists=[hp],
        )
        assert run.id == "abc-123"
        assert run.num == 7
        assert run.playlist_count == 1
        assert run.video_count == 10
        assert run.size_mb == 50.0
        assert run.merged is True
        assert len(run.playlists) == 1
        assert run.playlists[0].prefix == "P01"


# ---------------------------------------------------------------------------
# LogEntry
# ---------------------------------------------------------------------------

class TestLogEntryDefaults:
    def test_required_fields_stored(self):
        entry = LogEntry(t="2026-06-01T10:00:00", lvl="info", src="downloader", msg="started")
        assert entry.t == "2026-06-01T10:00:00"
        assert entry.lvl == "info"
        assert entry.src == "downloader"
        assert entry.msg == "started"

    def test_detail_defaults_to_none(self):
        entry = LogEntry(t="t", lvl="info", src="s", msg="m")
        assert entry.detail is None

    def test_code_defaults_to_none(self):
        entry = LogEntry(t="t", lvl="info", src="s", msg="m")
        assert entry.code is None

    def test_detail_can_be_set(self):
        entry = LogEntry(t="t", lvl="error", src="s", msg="failed", detail="stack trace here")
        assert entry.detail == "stack trace here"

    def test_code_can_be_set(self):
        entry = LogEntry(t="t", lvl="error", src="s", msg="failed", code="ERR_001")
        assert entry.code == "ERR_001"

    @pytest.mark.parametrize("lvl", ["error", "warn", "info", "debug"])
    def test_valid_log_levels(self, lvl):
        entry = LogEntry(t="t", lvl=lvl, src="s", msg="m")
        assert entry.lvl == lvl


class TestLogEntryMutability:
    def test_msg_can_be_updated(self):
        entry = LogEntry(t="t", lvl="info", src="s", msg="original")
        entry.msg = "updated"
        assert entry.msg == "updated"

    def test_detail_can_be_assigned_after_creation(self):
        entry = LogEntry(t="t", lvl="warn", src="s", msg="m")
        assert entry.detail is None
        entry.detail = "extra info"
        assert entry.detail == "extra info"


# ---------------------------------------------------------------------------
# HistoryPlaylist
# ---------------------------------------------------------------------------

class TestHistoryPlaylist:
    def test_fields_stored(self):
        hp = HistoryPlaylist(prefix="P02", title="Lectures", videos=20, size_mb=120.5, speed=1.25)
        assert hp.prefix == "P02"
        assert hp.title == "Lectures"
        assert hp.videos == 20
        assert hp.size_mb == 120.5
        assert hp.speed == 1.25

    def test_size_mb_is_float(self):
        hp = HistoryPlaylist(prefix="P01", title="T", videos=1, size_mb=0.5, speed=1.0)
        assert isinstance(hp.size_mb, float)

    def test_speed_stored_as_float(self):
        hp = HistoryPlaylist(prefix="P01", title="T", videos=1, size_mb=1.0, speed=2.0)
        assert hp.speed == 2.0
