"""Tests for backend/api/merge.py — MergeAPI."""
from __future__ import annotations

import threading
from unittest.mock import patch

import pytest


class TestMergeApiReturnType:
    def test_returns_two_element_tuple(self, tmp_path):
        from backend.api.merge import MergeAPI
        result = MergeAPI().merge([], str(tmp_path), str(tmp_path / "dest"))
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_first_element_is_int(self, tmp_path):
        from backend.api.merge import MergeAPI
        moved, _ = MergeAPI().merge([], str(tmp_path), str(tmp_path / "dest"))
        assert isinstance(moved, int)

    def test_second_element_is_list(self, tmp_path):
        from backend.api.merge import MergeAPI
        _, skipped = MergeAPI().merge([], str(tmp_path), str(tmp_path / "dest"))
        assert isinstance(skipped, list)

    def test_empty_playlists_returns_zero_moved(self, tmp_path):
        from backend.api.merge import MergeAPI
        moved, skipped = MergeAPI().merge([], str(tmp_path), str(tmp_path / "dest"))
        assert moved == 0
        assert skipped == []

    def test_stop_event_respected(self, tmp_path):
        from backend.api.merge import MergeAPI
        stop = threading.Event()
        stop.set()
        moved, _ = MergeAPI().merge(
            [], str(tmp_path), str(tmp_path / "dest"), stop=stop
        )
        assert moved == 0

    def test_on_log_receives_output_folder_message(self, tmp_path):
        from backend.api.merge import MergeAPI
        logs: list[str] = []
        MergeAPI().merge(
            [], str(tmp_path), str(tmp_path / "dest"), on_log=logs.append
        )
        assert any("Output folder" in m for m in logs)

    def test_creates_memory_card_directory(self, tmp_path):
        from backend.api.merge import MergeAPI
        dest = tmp_path / "dest"
        MergeAPI().merge([], str(tmp_path), str(dest))
        assert any("memory_card" in p.name for p in dest.iterdir())

    def test_creates_memory_audios_subdirectory(self, tmp_path):
        from backend.api.merge import MergeAPI
        dest = tmp_path / "dest"
        MergeAPI().merge([], str(tmp_path), str(dest))
        card = next(p for p in dest.iterdir() if "memory_card" in p.name)
        assert (card / "memory_audios").is_dir()
