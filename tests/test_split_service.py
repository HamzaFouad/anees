from __future__ import annotations
import os
import threading
from unittest.mock import MagicMock, patch, call

import pytest

from backend.services.split_service import SplitService


INPUT_PATH = "/tmp/audio/track.mp3"
BASE = "/tmp/audio/track"
OUT_DIR = "/tmp/audio"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(on_log=None):
    """Return a SplitService whose FfmpegClient is replaced by a MagicMock."""
    svc = SplitService(on_log=on_log)
    svc._client = MagicMock()
    return svc


# ---------------------------------------------------------------------------
# 1. File not found → returns []
# ---------------------------------------------------------------------------

def test_file_not_found_returns_empty_list():
    svc = _make_service()
    with patch("os.path.exists", return_value=False):
        result = svc.split_file(INPUT_PATH, chunk_min=10)
    assert result == []
    svc._client.split.assert_not_called()


# ---------------------------------------------------------------------------
# 2. File not found → on_log called with correct message
# ---------------------------------------------------------------------------

def test_file_not_found_logs_message():
    logs = []
    svc = _make_service(on_log=logs.append)
    with patch("os.path.exists", return_value=False):
        svc.split_file(INPUT_PATH, chunk_min=10)
    assert any("file not found" in m for m in logs)
    assert any(INPUT_PATH in m for m in logs)


# ---------------------------------------------------------------------------
# 3. ffmpeg returns non-zero (ok=False) → returns [input_path]
# ---------------------------------------------------------------------------

def test_ffmpeg_failure_returns_input_path():
    svc = _make_service()
    svc._client.split.return_value = False
    with patch("os.path.exists", return_value=True):
        result = svc.split_file(INPUT_PATH, chunk_min=5)
    assert result == [INPUT_PATH]


# ---------------------------------------------------------------------------
# 4. ffmpeg failure → on_log reports keep-original message
# ---------------------------------------------------------------------------

def test_ffmpeg_failure_logs_keep_original():
    logs = []
    svc = _make_service(on_log=logs.append)
    svc._client.split.return_value = False
    with patch("os.path.exists", return_value=True):
        svc.split_file(INPUT_PATH, chunk_min=5)
    assert any("keeping original" in m.lower() for m in logs)


# ---------------------------------------------------------------------------
# 5. ffmpeg success → deletes original, returns sorted parts
# ---------------------------------------------------------------------------

def test_ffmpeg_success_returns_sorted_parts_and_deletes_original():
    svc = _make_service()
    svc._client.split.return_value = True

    listed_files = ["track_part002.mp3", "track_part001.mp3", "track_part003.mp3",
                    "other_file.mp3"]

    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=listed_files),
        patch("os.remove") as mock_remove,
    ):
        result = svc.split_file(INPUT_PATH, chunk_min=10)

    expected = [
        os.path.join(OUT_DIR, "track_part001.mp3"),
        os.path.join(OUT_DIR, "track_part002.mp3"),
        os.path.join(OUT_DIR, "track_part003.mp3"),
    ]
    assert result == expected
    mock_remove.assert_called_once_with(INPUT_PATH)


# ---------------------------------------------------------------------------
# 6. ffmpeg success but no matching parts found → returns [input_path], no delete
# ---------------------------------------------------------------------------

def test_ffmpeg_success_no_parts_returns_input_path():
    svc = _make_service()
    svc._client.split.return_value = True

    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["unrelated.mp3", "README.txt"]),
        patch("os.remove") as mock_remove,
    ):
        result = svc.split_file(INPUT_PATH, chunk_min=10)

    assert result == [INPUT_PATH]
    mock_remove.assert_not_called()


# ---------------------------------------------------------------------------
# 7. Stop event mid-split → ffmpeg client receives the event; ok=False → [input]
# ---------------------------------------------------------------------------

def test_stop_event_passed_to_ffmpeg_client():
    svc = _make_service()
    svc._client.split.return_value = False
    stop = threading.Event()
    stop.set()

    with patch("os.path.exists", return_value=True):
        result = svc.split_file(INPUT_PATH, chunk_min=5, stop=stop)

    # The stop event must be forwarded to FfmpegClient.split
    _, _, _, _, forwarded_stop = svc._client.split.call_args.args
    assert forwarded_stop is stop
    assert result == [INPUT_PATH]


# ---------------------------------------------------------------------------
# 8. on_log callback receives messages during a successful split
# ---------------------------------------------------------------------------

def test_on_log_receives_split_messages():
    logs = []
    svc = _make_service(on_log=logs.append)
    svc._client.split.return_value = True

    listed_files = ["track_part001.mp3"]
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=listed_files),
        patch("os.remove"),
    ):
        svc.split_file(INPUT_PATH, chunk_min=3)

    # Must log the "splitting … chunks" intro and the "Split complete" summary
    assert any("chunk" in m.lower() for m in logs)
    assert any("split complete" in m.lower() for m in logs)


# ---------------------------------------------------------------------------
# 9. chunk_min is converted to seconds when calling FfmpegClient.split
# ---------------------------------------------------------------------------

def test_chunk_duration_passed_as_seconds():
    svc = _make_service()
    svc._client.split.return_value = False
    chunk_min = 7

    with patch("os.path.exists", return_value=True):
        svc.split_file(INPUT_PATH, chunk_min=chunk_min)

    _, _, duration_secs, _, _ = svc._client.split.call_args.args
    assert duration_secs == chunk_min * 60


# ---------------------------------------------------------------------------
# 10. Parts regex only matches files belonging to this stem (not other stems)
# ---------------------------------------------------------------------------

def test_parts_regex_excludes_other_stems():
    svc = _make_service()
    svc._client.split.return_value = True

    # "other_track_part001.mp3" must NOT be picked up for "track"
    listed_files = [
        "track_part001.mp3",
        "other_track_part001.mp3",
        "track_part002.mp3",
    ]
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=listed_files),
        patch("os.remove"),
    ):
        result = svc.split_file(INPUT_PATH, chunk_min=10)

    basenames = [os.path.basename(p) for p in result]
    assert "other_track_part001.mp3" not in basenames
    assert "track_part001.mp3" in basenames
    assert "track_part002.mp3" in basenames


# ---------------------------------------------------------------------------
# 11. OSError on os.remove is swallowed — result is still returned
# ---------------------------------------------------------------------------

def test_remove_oserror_is_swallowed():
    svc = _make_service()
    svc._client.split.return_value = True

    listed_files = ["track_part001.mp3"]
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=listed_files),
        patch("os.remove", side_effect=OSError("permission denied")),
    ):
        result = svc.split_file(INPUT_PATH, chunk_min=10)

    expected = [os.path.join(OUT_DIR, "track_part001.mp3")]
    assert result == expected


# ---------------------------------------------------------------------------
# 12. No on_log provided — default no-op lambda does not raise
# ---------------------------------------------------------------------------

def test_no_on_log_does_not_raise():
    svc = SplitService()  # no on_log
    svc._client = MagicMock()
    svc._client.split.return_value = False

    with patch("os.path.exists", return_value=True):
        result = svc.split_file(INPUT_PATH, chunk_min=5)

    assert result == [INPUT_PATH]
