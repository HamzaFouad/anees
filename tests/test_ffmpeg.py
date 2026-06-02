"""Tests for backend/commands/ffmpeg.py (FfmpegClient)."""
from __future__ import annotations

import math
import subprocess
import sys
import threading
from io import StringIO
from unittest.mock import MagicMock, patch, call

import pytest

from backend.commands.ffmpeg import FfmpegClient, _find_ffmpeg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proc(lines: list[str], returncode: int = 0) -> MagicMock:
    """Return a mock Popen object whose stdout yields the given lines."""
    proc = MagicMock()
    proc.stdout = iter(line + "\n" for line in lines)
    proc.wait.return_value = returncode
    return proc


# ---------------------------------------------------------------------------
# _find_ffmpeg
# ---------------------------------------------------------------------------

class TestFindFfmpeg:
    def test_returns_ffmpeg_when_not_frozen(self):
        with patch.object(sys, "frozen", False, create=True):
            with patch("os.path.exists", return_value=False):
                result = _find_ffmpeg()
        assert result == "ffmpeg"

    def test_returns_bundled_path_when_frozen(self, tmp_path):
        fake_meipass = str(tmp_path)
        binary = tmp_path / "ffmpeg"
        binary.touch()
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", fake_meipass, create=True):
                with patch("sys.platform", "linux"):
                    result = _find_ffmpeg()
        assert result == str(binary)

    def test_frozen_falls_back_to_ffmpeg_when_bundle_missing(self, tmp_path):
        fake_meipass = str(tmp_path)
        with patch.object(sys, "frozen", True, create=True):
            with patch.object(sys, "_MEIPASS", fake_meipass, create=True):
                with patch("sys.platform", "linux"):
                    result = _find_ffmpeg()
        assert result == "ffmpeg"


# ---------------------------------------------------------------------------
# FfmpegClient.split
# ---------------------------------------------------------------------------

class TestFfmpegClientSplit:
    def setup_method(self):
        self.client = FfmpegClient()
        self.stop = threading.Event()
        self.logs: list[str] = []

    def _on_log(self, line: str) -> None:
        self.logs.append(line)

    def test_split_success_returns_true(self):
        proc = _make_proc(["frame=100", "frame=200"], returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert result is True

    def test_split_nonzero_exit_returns_false(self):
        proc = _make_proc(["some output"], returncode=1)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert result is False

    def test_split_stop_event_terminates_and_returns_false(self):
        self.stop.set()
        proc = _make_proc(["line1", "line2"], returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert result is False
        proc.terminate.assert_called_once()

    def test_split_timeout_expired_calls_kill(self):
        self.stop.set()
        proc = _make_proc(["line1"], returncode=0)
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert result is False
        proc.kill.assert_called_once()

    def test_split_on_log_receives_each_line(self):
        lines = ["info line one", "info line two", "info line three"]
        proc = _make_proc(lines, returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert self.logs == lines

    def test_split_strips_trailing_whitespace_from_log(self):
        # _make_proc appends "\n"; rstrip() removes it along with trailing spaces
        proc = _make_proc(["  trimmed line  "], returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert self.logs == ["  trimmed line"]

    def test_split_popen_exception_returns_false_and_logs(self):
        with patch("subprocess.Popen", side_effect=OSError("not found")):
            result = self.client.split(
                "/in.mp3", "/out_%03d.mp3", 300, self._on_log, self.stop
            )
        assert result is False
        assert any("ffmpeg error" in msg for msg in self.logs)


# ---------------------------------------------------------------------------
# FfmpegClient.speed
# ---------------------------------------------------------------------------

class TestFfmpegClientSpeed:
    def setup_method(self):
        self.client = FfmpegClient()
        self.stop = threading.Event()
        self.logs: list[str] = []

    def _on_log(self, line: str) -> None:
        self.logs.append(line)

    def _captured_cmd(self, lines: list[str] = None, returncode: int = 0):
        """Context manager that patches Popen and returns the captured cmd list."""
        lines = lines or []
        proc = _make_proc(lines, returncode=returncode)
        patcher = patch("subprocess.Popen", return_value=proc)
        return patcher, proc

    def test_speed_single_atempo_filter_below_2(self):
        captured = []

        def fake_popen(cmd, **kwargs):
            captured.extend(cmd)
            return _make_proc([], returncode=0)

        with patch("subprocess.Popen", side_effect=fake_popen):
            self.client.speed("/in.mp3", "/out.mp3", 1.5, self._on_log, self.stop)

        af_index = captured.index("-af") + 1
        assert captured[af_index] == "atempo=1.5000"

    def test_speed_chained_atempo_filter_above_2(self):
        captured = []
        speed = 3.0
        factor = math.sqrt(speed)
        expected_af = f"atempo={factor:.4f},atempo={factor:.4f}"

        def fake_popen(cmd, **kwargs):
            captured.extend(cmd)
            return _make_proc([], returncode=0)

        with patch("subprocess.Popen", side_effect=fake_popen):
            self.client.speed("/in.mp3", "/out.mp3", speed, self._on_log, self.stop)

        af_index = captured.index("-af") + 1
        assert captured[af_index] == expected_af

    def test_speed_success_returns_true(self):
        proc = _make_proc([], returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.speed(
                "/in.mp3", "/out.mp3", 1.5, self._on_log, self.stop
            )
        assert result is True

    def test_speed_nonzero_exit_returns_false(self):
        proc = _make_proc([], returncode=2)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.speed(
                "/in.mp3", "/out.mp3", 1.5, self._on_log, self.stop
            )
        assert result is False

    def test_speed_stop_event_aborts_and_returns_false(self):
        self.stop.set()
        proc = _make_proc(["progress line"], returncode=0)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.speed(
                "/in.mp3", "/out.mp3", 1.5, self._on_log, self.stop
            )
        assert result is False
        proc.terminate.assert_called_once()

    def test_speed_timeout_expired_on_stop_calls_kill(self):
        self.stop.set()
        proc = _make_proc(["line"], returncode=0)
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=5)
        with patch("subprocess.Popen", return_value=proc):
            result = self.client.speed(
                "/in.mp3", "/out.mp3", 1.5, self._on_log, self.stop
            )
        assert result is False
        proc.kill.assert_called_once()

    def test_speed_popen_exception_returns_false_and_logs(self):
        with patch("subprocess.Popen", side_effect=FileNotFoundError("ffmpeg missing")):
            result = self.client.speed(
                "/in.mp3", "/out.mp3", 1.5, self._on_log, self.stop
            )
        assert result is False
        assert any("ffmpeg error" in msg for msg in self.logs)

    def test_speed_exactly_2_uses_single_filter(self):
        captured = []

        def fake_popen(cmd, **kwargs):
            captured.extend(cmd)
            return _make_proc([], returncode=0)

        with patch("subprocess.Popen", side_effect=fake_popen):
            self.client.speed("/in.mp3", "/out.mp3", 2.0, self._on_log, self.stop)

        af_index = captured.index("-af") + 1
        assert captured[af_index] == "atempo=2.0000"
        assert "," not in captured[af_index]
