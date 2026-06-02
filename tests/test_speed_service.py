"""Tests for backend/services/speed_service.py"""
from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, call, patch

import pytest

from backend.services.speed_service import SpeedService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _service(logs: list[str] | None = None) -> SpeedService:
    """Return a SpeedService whose on_log appends to *logs*."""
    collected: list[str] = [] if logs is None else logs
    svc = SpeedService(on_log=collected.append)
    return svc


# ---------------------------------------------------------------------------
# 1. Missing file — log warning, skip processing
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.path.exists", return_value=False)
@patch("backend.services.speed_service.FfmpegClient.speed")
def test_apply_speed_skips_missing_file(mock_speed, mock_exists):
    logs: list[str] = []
    svc = _service(logs)

    result = svc.apply_speed(["/missing/file.mp3"], speed=1.5)

    mock_speed.assert_not_called()
    assert result == ["/missing/file.mp3"]
    assert any("file not found" in msg for msg in logs)
    assert any("missing/file.mp3" in msg for msg in logs)


# ---------------------------------------------------------------------------
# 2. ffmpeg failure → delete tmp, log error, continue to next file
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.remove")
@patch("backend.services.speed_service.os.replace")
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=False)
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_ffmpeg_failure_deletes_tmp_and_continues(
    mock_exists, mock_speed, mock_replace, mock_remove
):
    logs: list[str] = []
    svc = _service(logs)
    paths = ["/a/one.mp3", "/a/two.mp3"]

    result = svc.apply_speed(paths, speed=1.5)

    # Both files attempted
    assert mock_speed.call_count == 2
    # os.replace never called on failure
    mock_replace.assert_not_called()
    # tmp cleanup attempted for both files
    assert mock_remove.call_count == 2
    mock_remove.assert_any_call("/a/one.mp3.spd.mp3")
    mock_remove.assert_any_call("/a/two.mp3.spd.mp3")
    # Error logged for each file
    assert any("failed for one.mp3" in msg for msg in logs)
    assert any("failed for two.mp3" in msg for msg in logs)
    assert result == paths


# ---------------------------------------------------------------------------
# 3. os.replace fails → RuntimeError raised
# ---------------------------------------------------------------------------

def _exists_side_effect(path: str) -> bool:
    """Source files exist; tmp file also exists after speed pass."""
    return True


@patch("backend.services.speed_service.os.remove")
@patch(
    "backend.services.speed_service.os.replace",
    side_effect=OSError("permission denied"),
)
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=True)
@patch("backend.services.speed_service.os.path.exists", side_effect=_exists_side_effect)
def test_apply_speed_replace_failure_raises_runtime_error(
    mock_exists, mock_speed, mock_replace, mock_remove
):
    svc = _service()

    with pytest.raises(RuntimeError, match="cannot replace file"):
        svc.apply_speed(["/a/file.mp3"], speed=1.5)

    # tmp cleanup attempted after failed replace
    mock_remove.assert_called_once_with("/a/file.mp3.spd.mp3")


# ---------------------------------------------------------------------------
# 4. Success → tmp replaced with original path, returns original list
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.replace")
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=True)
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_success_replaces_tmp(mock_exists, mock_speed, mock_replace):
    logs: list[str] = []
    svc = _service(logs)
    paths = ["/a/file.mp3"]

    result = svc.apply_speed(paths, speed=1.5)

    mock_replace.assert_called_once_with("/a/file.mp3.spd.mp3", "/a/file.mp3")
    assert result is paths
    assert any("Applying" in msg for msg in logs)


# ---------------------------------------------------------------------------
# 5. Stop event set before loop → no files processed
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.FfmpegClient.speed")
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_stop_event_breaks_early(mock_exists, mock_speed):
    stop = threading.Event()
    stop.set()

    svc = _service()
    result = svc.apply_speed(["/a/one.mp3", "/a/two.mp3"], speed=1.5, stop=stop)

    mock_speed.assert_not_called()
    assert result == ["/a/one.mp3", "/a/two.mp3"]


# ---------------------------------------------------------------------------
# 6. Stop event set mid-loop → only first file processed
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.replace")
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_stop_event_mid_loop(mock_exists, mock_replace):
    stop = threading.Event()
    call_count = 0

    def fake_speed(inp, out, spd, on_log, stop_ev):
        nonlocal call_count
        call_count += 1
        # Set stop after processing the first file so second is skipped
        stop_ev.set()
        return True

    with patch("backend.services.speed_service.FfmpegClient.speed", side_effect=fake_speed):
        svc = _service()
        svc.apply_speed(["/a/one.mp3", "/a/two.mp3"], speed=1.5, stop=stop)

    assert call_count == 1
    mock_replace.assert_called_once_with("/a/one.mp3.spd.mp3", "/a/one.mp3")


# ---------------------------------------------------------------------------
# 7. All files processed in order
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.replace")
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=True)
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_processes_all_files_in_order(mock_exists, mock_speed, mock_replace):
    paths = ["/a/one.mp3", "/a/two.mp3", "/a/three.mp3"]
    svc = _service()

    result = svc.apply_speed(paths, speed=1.25)

    assert mock_speed.call_count == 3
    # Verify input paths passed to speed() match original order
    input_paths_used = [c.args[0] for c in mock_speed.call_args_list]
    assert input_paths_used == paths
    assert result == paths


# ---------------------------------------------------------------------------
# 8. os.remove raises during tmp cleanup after ffmpeg failure — no crash
# ---------------------------------------------------------------------------

@patch(
    "backend.services.speed_service.os.remove",
    side_effect=OSError("file busy"),
)
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=False)
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_tmp_remove_error_does_not_crash(mock_exists, mock_speed, mock_remove):
    svc = _service()
    # Should not raise even though os.remove throws
    result = svc.apply_speed(["/a/file.mp3"], speed=1.5)
    assert result == ["/a/file.mp3"]


# ---------------------------------------------------------------------------
# 9. Speed value forwarded correctly to FfmpegClient.speed
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.replace")
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=True)
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_passes_correct_speed_to_client(mock_exists, mock_speed, mock_replace):
    svc = _service()
    svc.apply_speed(["/a/file.mp3"], speed=2.0)

    _, _, speed_arg, _, _ = mock_speed.call_args.args
    assert speed_arg == 2.0


# ---------------------------------------------------------------------------
# 10. No on_log provided — uses default no-op, does not crash
# ---------------------------------------------------------------------------

@patch("backend.services.speed_service.os.replace")
@patch("backend.services.speed_service.FfmpegClient.speed", return_value=True)
@patch("backend.services.speed_service.os.path.exists", return_value=True)
def test_apply_speed_no_on_log_does_not_crash(mock_exists, mock_speed, mock_replace):
    svc = SpeedService()  # no on_log
    result = svc.apply_speed(["/a/file.mp3"], speed=1.5)
    assert result == ["/a/file.mp3"]
    mock_replace.assert_called_once_with("/a/file.mp3.spd.mp3", "/a/file.mp3")
