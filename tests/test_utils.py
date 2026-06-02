"""Tests for backend/utils/audio.py, backend/utils/config.py, backend/api/stats.py."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.utils.audio import estimate_size_mb
from tests.conftest import make_playlist, make_video


# ---------------------------------------------------------------------------
# backend/utils/audio.py — estimate_size_mb
# ---------------------------------------------------------------------------

class TestEstimateSizeMb:
    def test_zero_duration_returns_zero(self):
        assert estimate_size_mb(0) == 0.0

    def test_negative_duration_returns_zero(self):
        assert estimate_size_mb(-10) == 0.0

    def test_60s_at_default_bitrate(self):
        # 60 * 192_000 / 8 / 1_048_576
        expected = round(60 * 192 * 1_000 / 8 / 1_048_576, 1)
        assert estimate_size_mb(60) == expected

    def test_60s_at_2x_is_half_of_1x(self):
        # speed does not affect estimate_size_mb directly — the caller
        # (playlist_size_estimate) divides duration by speed first.
        # Here we verify that halving the duration halves the result.
        full = estimate_size_mb(60)
        half = estimate_size_mb(30)
        assert half == round(full / 2, 1)

    def test_custom_bitrate_scales_linearly(self):
        size_192 = estimate_size_mb(60, bitrate_kbps=192)
        size_96  = estimate_size_mb(60, bitrate_kbps=96)
        # 96 kbps should produce exactly half the size of 192 kbps
        assert size_96 == round(size_192 / 2, 1)

    def test_return_type_is_float(self):
        result = estimate_size_mb(120)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# backend/utils/config.py — get_output_root, set_output_root, check_disk_space
# ---------------------------------------------------------------------------

class TestGetOutputRoot:
    def test_returns_default_when_config_missing(self, tmp_path):
        """When the config file does not exist _load() returns {} and the
        default path from _DEFAULTS is used."""
        fake_file = tmp_path / "config.json"
        # Patch _FILE so read_text raises FileNotFoundError (file absent)
        with patch("backend.utils.config._FILE", fake_file):
            from backend.utils.config import get_output_root
            result = get_output_root()
        from pathlib import Path
        expected = str(Path.home() / "Downloads" / "Anees")
        assert result == expected

    def test_returns_stored_value_when_config_exists(self, tmp_path):
        fake_file = tmp_path / "config.json"
        fake_file.write_text(json.dumps({"output_root": "/custom/path"}), encoding="utf-8")
        with patch("backend.utils.config._FILE", fake_file), \
             patch("backend.utils.config._DIR", tmp_path):
            from backend.utils.config import get_output_root
            assert get_output_root() == "/custom/path"


class TestSetOutputRoot:
    def test_set_then_get_reflects_change(self, tmp_path):
        fake_file = tmp_path / "config.json"
        with patch("backend.utils.config._FILE", fake_file), \
             patch("backend.utils.config._DIR", tmp_path):
            from backend.utils.config import get_output_root, set_output_root
            set_output_root("/new/output/dir")
            assert get_output_root() == "/new/output/dir"

    def test_set_writes_valid_json_to_disk(self, tmp_path):
        fake_file = tmp_path / "config.json"
        with patch("backend.utils.config._FILE", fake_file), \
             patch("backend.utils.config._DIR", tmp_path):
            from backend.utils.config import set_output_root
            set_output_root("/written/path")
        stored = json.loads(fake_file.read_text(encoding="utf-8"))
        assert stored["output_root"] == "/written/path"

    def test_set_preserves_existing_keys(self, tmp_path):
        fake_file = tmp_path / "config.json"
        fake_file.write_text(json.dumps({"other_key": "value"}), encoding="utf-8")
        with patch("backend.utils.config._FILE", fake_file), \
             patch("backend.utils.config._DIR", tmp_path):
            from backend.utils.config import set_output_root
            set_output_root("/some/path")
        stored = json.loads(fake_file.read_text(encoding="utf-8"))
        assert stored["other_key"] == "value"
        assert stored["output_root"] == "/some/path"


class TestCheckDiskSpace:
    def _make_usage(self, free_bytes: int):
        usage = MagicMock()
        usage.free = free_bytes
        return usage

    def test_sufficient_space_returns_true(self, tmp_path):
        # Need 10 MB with 20 % margin → required = 12 MB; free = 100 MB
        free_mb = 100
        with patch("shutil.disk_usage", return_value=self._make_usage(free_mb * 1024 * 1024)):
            from backend.utils.config import check_disk_space
            ok, required_mb, reported_free = check_disk_space(10.0, str(tmp_path))
        assert ok is True
        assert required_mb == pytest.approx(12.0)
        assert reported_free == pytest.approx(free_mb, rel=1e-3)

    def test_insufficient_space_returns_false(self, tmp_path):
        # Need 100 MB with 20 % margin → required = 120 MB; free = 50 MB
        free_mb = 50
        with patch("shutil.disk_usage", return_value=self._make_usage(free_mb * 1024 * 1024)):
            from backend.utils.config import check_disk_space
            ok, required_mb, reported_free = check_disk_space(100.0, str(tmp_path))
        assert ok is False
        assert required_mb == pytest.approx(120.0)
        assert reported_free == pytest.approx(free_mb, rel=1e-3)

    def test_exception_in_disk_usage_returns_true(self, tmp_path):
        with patch("shutil.disk_usage", side_effect=OSError("no device")):
            from backend.utils.config import check_disk_space
            ok, required_mb, free = check_disk_space(50.0, str(tmp_path))
        assert ok is True
        assert required_mb == 0.0
        assert free == 0.0

    def test_margin_is_applied(self, tmp_path):
        free_mb = 130
        with patch("shutil.disk_usage", return_value=self._make_usage(free_mb * 1024 * 1024)):
            from backend.utils.config import check_disk_space
            # With default 20 % margin: required = 100 * 1.2 = 120 — should pass
            ok, required_mb, _ = check_disk_space(100.0, str(tmp_path))
        assert ok is True
        assert required_mb == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# backend/api/stats.py — playlist_size_estimate, playlist_total_duration
# ---------------------------------------------------------------------------

class TestPlaylistSizeEstimate:
    def test_empty_playlist_returns_zero(self):
        from backend.api.stats import playlist_size_estimate
        pl = make_playlist(videos=[])
        assert playlist_size_estimate(pl) == 0.0

    def test_single_video_matches_audio_estimate(self):
        from backend.api.stats import playlist_size_estimate
        video = make_video(duration=60)
        pl = make_playlist(videos=[video])
        expected = estimate_size_mb(60)
        assert playlist_size_estimate(pl) == expected

    def test_multiple_videos_sum_durations(self):
        from backend.api.stats import playlist_size_estimate
        videos = [make_video(duration=60), make_video(duration=120), make_video(duration=30)]
        pl = make_playlist(videos=videos)
        expected = estimate_size_mb(60 + 120 + 30)
        assert playlist_size_estimate(pl) == expected


class TestPlaylistTotalDuration:
    def test_empty_playlist_returns_zero(self):
        from backend.api.stats import playlist_total_duration
        pl = make_playlist(videos=[])
        assert playlist_total_duration(pl) == 0

    def test_single_video(self):
        from backend.api.stats import playlist_total_duration
        pl = make_playlist(videos=[make_video(duration=180)])
        assert playlist_total_duration(pl) == 180

    def test_multiple_videos_summed(self):
        from backend.api.stats import playlist_total_duration
        videos = [make_video(duration=60), make_video(duration=90), make_video(duration=150)]
        pl = make_playlist(videos=videos)
        assert playlist_total_duration(pl) == 300

    def test_return_type_is_int(self):
        from backend.api.stats import playlist_total_duration
        pl = make_playlist(videos=[make_video(duration=60)])
        assert isinstance(playlist_total_duration(pl), int)
