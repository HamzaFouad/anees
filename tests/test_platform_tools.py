"""Tests for backend/platform resources and tool helpers."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


class TestResources:
    def test_app_root_points_to_repo_when_not_frozen(self, monkeypatch):
        from backend.platform import resources

        monkeypatch.setattr(sys, "frozen", False, raising=False)
        root = resources.app_root()
        assert (root / "main.py").exists()

    def test_app_root_uses_meipass_when_frozen(self, tmp_path, monkeypatch):
        from backend.platform import resources

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        assert resources.app_root() == tmp_path

    def test_app_icon_path_returns_mac_icns_when_present(self, tmp_path, monkeypatch):
        from backend.platform import resources

        (tmp_path / "images").mkdir(parents=True)
        icns = tmp_path / "images" / "anees.icns"
        icns.touch()
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        with patch("sys.platform", "darwin"):
            assert resources.app_icon_path() == icns


class TestTools:
    def test_ffmpeg_exe_prefers_bundled_binary_when_frozen(self, tmp_path, monkeypatch):
        from backend.platform.tools import ffmpeg_exe

        exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        bundled = tmp_path / exe_name
        bundled.touch()
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
        assert ffmpeg_exe() == str(bundled)

    def test_ffmpeg_exe_falls_back_to_path_binary(self, monkeypatch):
        from backend.platform.tools import ffmpeg_exe

        monkeypatch.setattr(sys, "frozen", False, raising=False)
        with patch("os.path.exists", return_value=False):
            assert ffmpeg_exe() == "ffmpeg"

    def test_ffmpeg_ok_true_on_zero_returncode(self):
        from backend.platform.tools import ffmpeg_ok

        result = MagicMock()
        result.returncode = 0
        with patch("subprocess.run", return_value=result):
            assert ffmpeg_ok() is True

    def test_ffmpeg_version_parses_stdout(self):
        from backend.platform.tools import ffmpeg_version

        result = MagicMock()
        result.stdout = "ffmpeg version 7.0.2 Copyright"
        with patch("subprocess.run", return_value=result):
            assert ffmpeg_version() == "7.0.2"
