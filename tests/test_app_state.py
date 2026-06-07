"""Tests for ui/state.py — AppState logic (no network, no download workers)."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.models import RunState
from tests.conftest import make_playlist, make_video


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def state(qapp):
    from ui.state import AppState
    return AppState()


def _add(state, pl):
    """Add a playlist without triggering a network fetch."""
    with patch.object(state, "_fetch_info_async"):
        state.add_playlist(pl)


# ---------------------------------------------------------------------------
# add_playlist
# ---------------------------------------------------------------------------

class TestAddPlaylist:
    def test_appends_to_playlists(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        assert pl in state.playlists

    def test_sets_selected_id_to_new_playlist(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        assert state.selected_id == pl.id

    def test_playlists_changed_signal_emitted(self, state):
        pl = make_playlist("P01")
        fired: list = []
        state.playlists_changed.connect(lambda: fired.append(True))
        _add(state, pl)
        assert fired

    def test_selection_changed_signal_emitted_with_playlist_id(self, state):
        pl = make_playlist("P01")
        received: list[str] = []
        state.selection_changed.connect(received.append)
        _add(state, pl)
        assert pl.id in received

    def test_multiple_adds_all_in_list(self, state):
        pl1 = make_playlist("P01")
        pl2 = make_playlist("P02")
        _add(state, pl1)
        _add(state, pl2)
        assert pl1 in state.playlists
        assert pl2 in state.playlists


# ---------------------------------------------------------------------------
# remove_playlist
# ---------------------------------------------------------------------------

class TestRemovePlaylist:
    def test_removes_playlist_from_list(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        state.remove_playlist(pl.id)
        assert pl not in state.playlists

    def test_clears_selection_when_last_removed(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        state.remove_playlist(pl.id)
        assert state.selected_id == ""

    def test_selection_moves_to_first_remaining(self, state):
        pl1 = make_playlist("P01")
        pl2 = make_playlist("P02")
        _add(state, pl1)
        _add(state, pl2)
        state.set_selected(pl1.id)
        state.remove_playlist(pl1.id)
        assert state.selected_id == pl2.id

    def test_playlists_changed_emitted(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        fired: list = []
        state.playlists_changed.connect(lambda: fired.append(True))
        state.remove_playlist(pl.id)
        assert fired

    def test_removing_unknown_id_does_not_raise(self, state):
        state.remove_playlist("no-such-id")

    def test_non_selected_removal_keeps_selection(self, state):
        pl1 = make_playlist("P01")
        pl2 = make_playlist("P02")
        _add(state, pl1)
        _add(state, pl2)
        state.set_selected(pl2.id)
        state.remove_playlist(pl1.id)
        assert state.selected_id == pl2.id


# ---------------------------------------------------------------------------
# reorder_playlist
# ---------------------------------------------------------------------------

class TestReorderPlaylist:
    def test_moves_last_item_to_front(self, state):
        for i in range(3):
            _add(state, make_playlist(f"P0{i}"))
        last_id = state.playlists[-1].id
        state.reorder_playlist(last_id, 0)
        assert state.playlists[0].id == last_id

    def test_moves_first_item_toward_end(self, state):
        for i in range(3):
            _add(state, make_playlist(f"P0{i}"))
        first_id = state.playlists[0].id
        state.reorder_playlist(first_id, 2)
        new_index = next(i for i, p in enumerate(state.playlists) if p.id == first_id)
        assert new_index != 0

    def test_prefixes_renumbered_as_zero_padded(self, state):
        for i in range(3):
            _add(state, make_playlist(f"P0{i}"))
        last_id = state.playlists[-1].id
        state.reorder_playlist(last_id, 0)
        for i, pl in enumerate(state.playlists):
            assert pl.prefix == str(i).zfill(2)

    def test_unknown_id_is_silently_ignored(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        original = list(state.playlists)
        state.reorder_playlist("nonexistent-id", 0)
        assert list(state.playlists) == original

    def test_playlists_changed_emitted_after_reorder(self, state):
        for i in range(2):
            _add(state, make_playlist(f"P0{i}"))
        fired: list = []
        state.playlists_changed.connect(lambda: fired.append(True))
        state.reorder_playlist(state.playlists[0].id, 1)
        assert fired


# ---------------------------------------------------------------------------
# set_view / set_query
# ---------------------------------------------------------------------------

class TestViewAndQuery:
    def test_set_view_updates_property(self, state):
        state.set_view("history")
        assert state.view == "history"

    def test_set_view_emits_view_changed(self, state):
        received: list[str] = []
        state.view_changed.connect(received.append)
        state.set_view("logs")
        assert "logs" in received

    def test_set_query_updates_property(self, state):
        state.set_query("huberman")
        assert state.query == "huberman"

    def test_set_query_emits_query_changed(self, state):
        received: list[str] = []
        state.query_changed.connect(received.append)
        state.set_query("test")
        assert "test" in received

    def test_empty_query_clears_filter(self, state):
        state.set_query("something")
        state.set_query("")
        assert state.query == ""


# ---------------------------------------------------------------------------
# locked property
# ---------------------------------------------------------------------------

class TestLockedProperty:
    def test_not_locked_when_idle(self, state):
        state._set_run_state(RunState.IDLE)
        assert not state.locked

    def test_not_locked_when_complete(self, state):
        state._set_run_state(RunState.COMPLETE)
        assert not state.locked

    def test_locked_when_running(self, state):
        state._set_run_state(RunState.RUNNING)
        assert state.locked

    def test_locked_when_paused(self, state):
        state._set_run_state(RunState.PAUSED)
        assert state.locked

    def test_run_state_changed_signal_emitted(self, state):
        received: list[RunState] = []
        state.run_state_changed.connect(received.append)
        state._set_run_state(RunState.RUNNING)
        assert RunState.RUNNING in received


# ---------------------------------------------------------------------------
# counts()
# ---------------------------------------------------------------------------

class TestCounts:
    def test_empty_state_all_zeros(self, state):
        counts = state.counts()
        assert counts["queued"] == 0
        assert counts["done"] == 0
        assert counts["videos_total"] == 0
        assert counts["videos_done"] == 0
        assert counts["videos_failed"] == 0

    def test_counts_queued_playlists(self, state):
        _add(state, make_playlist("P01"))
        _add(state, make_playlist("P02"))
        assert state.counts()["queued"] == 2

    def test_counts_video_totals(self, state):
        pl = make_playlist("P01", videos=[make_video() for _ in range(5)])
        _add(state, pl)
        assert state.counts()["videos_total"] == 5

    def test_counts_failed_videos_across_playlists(self, state):
        v_fail = [make_video(stage="failed") for _ in range(2)]
        v_done = [make_video(stage="done") for _ in range(3)]
        pl = make_playlist("P01", videos=v_fail + v_done)
        _add(state, pl)
        assert state.counts()["videos_failed"] == 2


# ---------------------------------------------------------------------------
# selected_playlist()
# ---------------------------------------------------------------------------

class TestSelectedPlaylist:
    def test_returns_correct_playlist(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        state.set_selected(pl.id)
        assert state.selected_playlist() is pl

    def test_returns_none_when_no_playlists(self, state):
        assert state.selected_playlist() is None

    def test_returns_none_for_stale_selection(self, state):
        state._selected = "ghost-id"
        assert state.selected_playlist() is None

    def test_set_selected_emits_selection_changed(self, state):
        pl = make_playlist("P01")
        _add(state, pl)
        received: list[str] = []
        state.selection_changed.connect(received.append)
        state.set_selected(pl.id)
        assert pl.id in received
