"""Shared fixtures for Anees test suite."""
from __future__ import annotations

import threading
import pytest

from backend.models import Playlist, Video


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


def make_video(
    title: str = "Test Video",
    stage: str = "queued",
    duration: int = 180,
    progress: float = 0.0,
    error: str | None = None,
) -> Video:
    return Video(
        title=title,
        duration_sec=duration,
        stage=stage,
        progress=progress,
        failed_at=stage if stage == "failed" else None,
        error=error,
    )


def make_playlist(
    prefix: str = "P01",
    title: str = "Test Playlist",
    url: str = "https://www.youtube.com/playlist?list=TEST",
    videos: list[Video] | None = None,
) -> Playlist:
    video_list = videos if videos is not None else []
    return Playlist(
        id=f"{prefix}-id",
        prefix=prefix,
        title=title,
        url=url,
        video_count=len(video_list),
        completed=sum(1 for v in video_list if v.stage == "done"),
        status="queued",
        active_stage="queued",
        speed=1.0,
        split_enabled=False,
        split_min=30,
        size_mb=None,
        added_at="2026-06-01T00:00:00",
        videos=video_list,
    )


@pytest.fixture
def mock_stop() -> threading.Event:
    event = threading.Event()
    return event


@pytest.fixture
def stopped_event() -> threading.Event:
    event = threading.Event()
    event.set()
    return event
