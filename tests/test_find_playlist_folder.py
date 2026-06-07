"""Tests for _find_playlist_folder() in merge_service — real filesystem."""
from __future__ import annotations

import pytest

from backend.services.merge_service import _find_playlist_folder


class TestFindPlaylistFolder:
    def test_finds_folder_by_prefix(self, tmp_path):
        (tmp_path / "P01_My Playlist").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result == str(tmp_path / "P01_My Playlist")

    def test_returns_none_when_no_prefix_match(self, tmp_path):
        (tmp_path / "P02_Other").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result is None

    def test_returns_none_for_nonexistent_root(self):
        result = _find_playlist_folder("/nonexistent/xyz/abc123", "P01")
        assert result is None

    def test_ignores_files_not_directories(self, tmp_path):
        (tmp_path / "P01_file.mp3").touch()
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result is None

    def test_does_not_match_shorter_prefix(self, tmp_path):
        # prefix "P0" must NOT match a dir named "P01_Playlist" (check is for "P0_")
        (tmp_path / "P01_Playlist").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P0")
        assert result is None

    def test_does_not_match_longer_prefix(self, tmp_path):
        # prefix "P011" must NOT match "P01_Playlist"
        (tmp_path / "P01_Playlist").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P011")
        assert result is None

    def test_empty_root_returns_none(self, tmp_path):
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result is None

    def test_sanitized_folder_name_still_found(self, tmp_path):
        # On-disk name may have underscores replacing special characters in the title
        (tmp_path / "P01_My___Podcast___Title").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result is not None
        assert "P01_" in result

    def test_finds_correct_prefix_among_many(self, tmp_path):
        for prefix in ("P01", "P02", "P03"):
            (tmp_path / f"{prefix}_Content").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P02")
        assert result is not None
        assert result.endswith("P02_Content")

    def test_returns_full_absolute_path(self, tmp_path):
        (tmp_path / "P01_Test").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result == str(tmp_path / "P01_Test")

    def test_prefix_with_leading_zeros(self, tmp_path):
        (tmp_path / "00_First Playlist").mkdir()
        result = _find_playlist_folder(str(tmp_path), "00")
        assert result is not None

    def test_prefix_only_no_underscore_suffix_not_matched(self, tmp_path):
        # A directory named exactly "P01" (no underscore) must not match
        (tmp_path / "P01").mkdir()
        result = _find_playlist_folder(str(tmp_path), "P01")
        assert result is None
