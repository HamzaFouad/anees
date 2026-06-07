"""Tests for backend/commands/ffmpeg.py — ffmpeg_ok() and _find_ffmpeg()."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# ffmpeg_ok()
# ---------------------------------------------------------------------------

class TestFfmpegOk:
    def test_returns_true_when_returncode_zero(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result):
            assert ffmpeg_ok() is True

    def test_returns_false_for_nonzero_returncode(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        result = MagicMock()
        result.returncode = 1
        with patch("subprocess.run", return_value=result):
            assert ffmpeg_ok() is False

    def test_returns_false_when_binary_not_found(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        with patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
            assert ffmpeg_ok() is False

    def test_returns_false_on_timeout(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 5)):
            assert ffmpeg_ok() is False

    def test_returns_false_on_permission_error(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        with patch("subprocess.run", side_effect=PermissionError("denied")):
            assert ffmpeg_ok() is False

    def test_passes_version_flag_to_process(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result) as mock_run:
            ffmpeg_ok()
        cmd = mock_run.call_args[0][0]
        assert "-version" in cmd

    def test_uses_5_second_timeout(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result) as mock_run:
            ffmpeg_ok()
        assert mock_run.call_args.kwargs.get("timeout") == 5

    def test_capture_output_enabled(self):
        from backend.commands.ffmpeg import ffmpeg_ok
        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result) as mock_run:
            ffmpeg_ok()
        assert mock_run.call_args.kwargs.get("capture_output") is True


# ---------------------------------------------------------------------------
# _find_ffmpeg()
# ---------------------------------------------------------------------------

class TestFindFfmpeg:
    def test_returns_non_empty_string(self):
        from backend.commands.ffmpeg import _find_ffmpeg
        result = _find_ffmpeg()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_frozen_uses_bundled_binary_when_present(self, tmp_path, monkeypatch):
        from backend.commands.ffmpeg import _find_ffmpeg
        exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        bundled = tmp_path / exe_name
        bundled.touch()

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

        result = _find_ffmpeg()
        assert result == str(bundled)

    def test_frozen_falls_through_when_bundled_missing(self, tmp_path, monkeypatch):
        from backend.commands.ffmpeg import _find_ffmpeg
        # _MEIPASS points to an empty dir — no bundled binary
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

        with patch("os.path.exists", return_value=False):
            result = _find_ffmpeg()

        # must still return a string — either a homebrew path or "ffmpeg"
        assert isinstance(result, str)
        assert "ffmpeg" in result.lower()

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_homebrew_opt_path_preferred_on_macos(self, monkeypatch):
        from backend.commands.ffmpeg import _find_ffmpeg
        monkeypatch.setattr(sys, "frozen", False, raising=False)

        with patch("os.path.exists", side_effect=lambda p: p == "/opt/homebrew/bin/ffmpeg"):
            result = _find_ffmpeg()

        assert result == "/opt/homebrew/bin/ffmpeg"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")
    def test_usr_local_fallback_on_macos(self, monkeypatch):
        from backend.commands.ffmpeg import _find_ffmpeg
        monkeypatch.setattr(sys, "frozen", False, raising=False)

        with patch("os.path.exists", side_effect=lambda p: p == "/usr/local/bin/ffmpeg"):
            result = _find_ffmpeg()

        assert result == "/usr/local/bin/ffmpeg"

    def test_final_fallback_is_path_ffmpeg(self, monkeypatch):
        from backend.commands.ffmpeg import _find_ffmpeg
        monkeypatch.setattr(sys, "frozen", False, raising=False)

        with patch("os.path.exists", return_value=False):
            result = _find_ffmpeg()

        assert result == "ffmpeg"
