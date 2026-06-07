"""Tests for backend/types.py status enums."""
from __future__ import annotations

from backend.types import PlaylistStatus, VideoStage


def test_video_stage_values_are_stable():
    assert VideoStage.QUEUED == "queued"
    assert VideoStage.DOWNLOAD == "download"
    assert VideoStage.MP3 == "mp3"
    assert VideoStage.SPEED == "speed"
    assert VideoStage.SPLIT == "split"
    assert VideoStage.DONE == "done"
    assert VideoStage.FAILED == "failed"


def test_playlist_status_values_are_stable():
    assert PlaylistStatus.QUEUED == "queued"
    assert PlaylistStatus.ACTIVE == "active"
    assert PlaylistStatus.PAUSED == "paused"
    assert PlaylistStatus.DONE == "done"
    assert PlaylistStatus.FAILED == "failed"
    assert PlaylistStatus.CANCELLED == "cancelled"
