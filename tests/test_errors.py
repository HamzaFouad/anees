"""Tests for backend/errors.py."""
from __future__ import annotations

from backend.errors import (
    AneesError,
    CancelledError,
    DownloadFailedError,
    FfmpegMissingError,
    InvalidOutputFolderError,
)


def test_base_error_fields():
    err = AneesError(
        user_message="User-safe",
        code="ANEES-X-001",
        technical_message="tech details",
        recoverable=False,
    )
    assert err.user_message == "User-safe"
    assert err.code == "ANEES-X-001"
    assert err.technical_message == "tech details"
    assert err.recoverable is False


def test_specialized_error_codes_are_stable():
    assert FfmpegMissingError().code == "ANEES-FFMPEG-001"
    assert DownloadFailedError().code == "ANEES-DL-001"
    assert InvalidOutputFolderError().code == "ANEES-FS-001"
    assert CancelledError().code == "ANEES-RUN-001"
