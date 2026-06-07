"""Tests for ui/workers/merge_worker.py — signal types and emission."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class TestMergeWorker:
    def test_completed_emits_moved_count(self, qapp, tmp_path):
        from ui.workers.merge_worker import MergeWorker
        worker = MergeWorker([], str(tmp_path), str(tmp_path / "dest"))

        results: list = []
        worker.completed.connect(lambda n, sk: results.append((n, sk)))

        with patch("backend.api.merge.MergeAPI.merge", return_value=(7, [])):
            worker.run()

        assert len(results) == 1
        assert results[0][0] == 7

    def test_completed_emits_skipped_list(self, qapp, tmp_path):
        from ui.workers.merge_worker import MergeWorker
        worker = MergeWorker([], str(tmp_path), str(tmp_path / "dest"))

        results: list = []
        worker.completed.connect(lambda n, sk: results.append((n, sk)))

        with patch("backend.api.merge.MergeAPI.merge", return_value=(3, ["pl_a", "pl_b"])):
            worker.run()

        assert results[0][1] == ["pl_a", "pl_b"]

    def test_failed_signal_emitted_on_exception(self, qapp, tmp_path):
        from ui.workers.merge_worker import MergeWorker
        worker = MergeWorker([], str(tmp_path), str(tmp_path / "dest"))

        errors: list[str] = []
        worker.failed.connect(errors.append)

        with patch("backend.api.merge.MergeAPI.merge", side_effect=RuntimeError("disk full")):
            worker.run()

        assert len(errors) == 1
        assert "disk full" in errors[0]

    def test_completed_not_emitted_after_stop(self, qapp, tmp_path):
        from ui.workers.merge_worker import MergeWorker
        worker = MergeWorker([], str(tmp_path), str(tmp_path / "dest"))
        worker.stop()  # set stop before run()

        results: list = []
        worker.completed.connect(lambda n, sk: results.append((n, sk)))

        with patch("backend.api.merge.MergeAPI.merge", return_value=(0, [])):
            worker.run()

        assert len(results) == 0

    def test_log_forwarded_via_log_added_signal(self, qapp, tmp_path):
        from ui.workers.merge_worker import MergeWorker
        worker = MergeWorker([], str(tmp_path), str(tmp_path / "dest"))

        logs: list[str] = []
        worker.log_added.connect(lambda lvl, msg: logs.append(msg))

        def fake_merge(*args, **kwargs):
            kwargs["on_log"]("hello from merge")
            return (0, [])

        with patch("backend.api.merge.MergeAPI.merge", side_effect=fake_merge):
            worker.run()

        assert "hello from merge" in logs

    def test_progress_forwarded_via_progress_signal(self, qapp, tmp_path):
        from ui.workers.merge_worker import MergeWorker
        worker = MergeWorker([], str(tmp_path), str(tmp_path / "dest"))

        progress_calls: list = []
        worker.progress.connect(lambda c, t: progress_calls.append((c, t)))

        def fake_merge(*args, **kwargs):
            kwargs["on_progress"](1, 5)
            kwargs["on_progress"](5, 5)
            return (5, [])

        with patch("backend.api.merge.MergeAPI.merge", side_effect=fake_merge):
            worker.run()

        assert (1, 5) in progress_calls
        assert (5, 5) in progress_calls
