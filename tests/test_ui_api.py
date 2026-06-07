"""Tests for ui/api/ — QueueAPI, RunAPI, NavAPI delegate correctly to AppState."""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.models import RunState
from tests.conftest import make_playlist


# ---------------------------------------------------------------------------
# QueueAPI
# ---------------------------------------------------------------------------

class TestQueueAPI:
    def _api(self):
        from ui.api.queue import QueueAPI
        state = MagicMock()
        return QueueAPI(state), state

    def test_add_delegates_to_add_playlist(self):
        api, state = self._api()
        pl = make_playlist("P01")
        api.add(pl)
        state.add_playlist.assert_called_once_with(pl)

    def test_remove_delegates_to_remove_playlist(self):
        api, state = self._api()
        api.remove("my-id")
        state.remove_playlist.assert_called_once_with("my-id")

    def test_select_delegates_to_set_selected(self):
        api, state = self._api()
        api.select("pid-123")
        state.set_selected.assert_called_once_with("pid-123")

    def test_search_delegates_to_set_query(self):
        api, state = self._api()
        api.search("huberman")
        state.set_query.assert_called_once_with("huberman")

    def test_reorder_delegates_to_reorder_playlist(self):
        api, state = self._api()
        api.reorder("pid-123", 2)
        state.reorder_playlist.assert_called_once_with("pid-123", 2)

    def test_search_empty_string_delegates(self):
        api, state = self._api()
        api.search("")
        state.set_query.assert_called_once_with("")

    def test_reorder_to_zero_index(self):
        api, state = self._api()
        api.reorder("pid-xyz", 0)
        state.reorder_playlist.assert_called_once_with("pid-xyz", 0)


# ---------------------------------------------------------------------------
# RunAPI
# ---------------------------------------------------------------------------

class TestRunAPI:
    def _api(self):
        from ui.api.run import RunAPI
        state = MagicMock()
        return RunAPI(state), state

    def test_start_calls_set_run_state_running(self):
        api, state = self._api()
        api.start()
        state.set_run_state.assert_called_once_with(RunState.RUNNING)

    def test_pause_calls_set_run_state_paused(self):
        api, state = self._api()
        api.pause()
        state.set_run_state.assert_called_once_with(RunState.PAUSED)

    def test_resume_calls_set_run_state_running(self):
        api, state = self._api()
        api.resume()
        state.set_run_state.assert_called_once_with(RunState.RUNNING)

    def test_stop_calls_set_run_state_idle(self):
        api, state = self._api()
        api.stop()
        state.set_run_state.assert_called_once_with(RunState.IDLE)


# ---------------------------------------------------------------------------
# NavAPI
# ---------------------------------------------------------------------------

class TestNavAPI:
    def _api(self):
        from ui.api.nav import NavAPI
        state = MagicMock()
        return NavAPI(state), state

    def test_go_calls_set_view(self):
        api, state = self._api()
        api.go("history")
        state.set_view.assert_called_once_with("history")

    def test_go_queue_navigates_to_queue(self):
        api, state = self._api()
        api.go_queue()
        state.set_view.assert_called_once_with("queue")

    def test_go_history_navigates_to_history(self):
        api, state = self._api()
        api.go_history()
        state.set_view.assert_called_once_with("history")

    def test_go_logs_navigates_to_logs(self):
        api, state = self._api()
        api.go_logs()
        state.set_view.assert_called_once_with("logs")
