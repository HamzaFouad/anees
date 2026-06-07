"""Shared typed status enums for state and pipeline stages."""
from __future__ import annotations

from enum import Enum


class VideoStage(str, Enum):
    QUEUED = "queued"
    DOWNLOAD = "download"
    MP3 = "mp3"
    SPEED = "speed"
    SPLIT = "split"
    DONE = "done"
    FAILED = "failed"


class PlaylistStatus(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
