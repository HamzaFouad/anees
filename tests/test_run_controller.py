"""Tests for backend/app_state/run_controller.py."""
from __future__ import annotations

from backend.app_state.run_controller import RunController


class _Signal:
    def __init__(self):
        self._slots = []

    def connect(self, slot):
        self._slots.append(slot)

    def emit(self, *args):
        for slot in list(self._slots):
            slot(*args)


class _DownloadWorker:
    def __init__(self):
        self.videos_ready = _Signal()
        self.video_stage = _Signal()
        self.video_meta = _Signal()
        self.log_added = _Signal()
        self.run_complete = _Signal()
        self.started = False
        self.paused = False
        self.resumed = False
        self.stopped = False
        self.wait_ms = None

    def start(self):
        self.started = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.resumed = True

    def stop(self):
        self.stopped = True

    def wait(self, ms):
        self.wait_ms = ms


class _RetryWorker:
    def __init__(self):
        self.video_stage = _Signal()
        self.video_meta = _Signal()
        self.log_added = _Signal()
        self.completed = _Signal()
        self.started = False
        self.deleted = False

    def start(self):
        self.started = True

    def deleteLater(self):
        self.deleted = True


class _InfoWorker:
    def __init__(self):
        self.info_ready = _Signal()
        self.finished = _Signal()
        self.started = False
        self.deleted = False

    def start(self):
        self.started = True

    def deleteLater(self):
        self.deleted = True


def _make_controller(download_worker, retry_worker, info_worker):
    callbacks = {
        "videos_ready": [],
        "video_stage": [],
        "video_meta": [],
        "log": [],
        "run_complete": [],
        "retry_complete": [],
    }
    controller = RunController(
        make_download_worker=lambda playlists, root: download_worker,
        make_retry_worker=lambda pl, idxs, root: retry_worker,
        make_info_worker=lambda pid, url: info_worker,
        on_videos_ready=lambda *a: callbacks["videos_ready"].append(a),
        on_video_stage=lambda *a: callbacks["video_stage"].append(a),
        on_video_meta=lambda *a: callbacks["video_meta"].append(a),
        on_log=lambda *a: callbacks["log"].append(a),
        on_run_complete=lambda: callbacks["run_complete"].append(True),
        on_retry_complete=lambda: callbacks["retry_complete"].append(True),
    )
    return controller, callbacks


def test_start_run_starts_worker_when_pending():
    d = _DownloadWorker()
    r = _RetryWorker()
    i = _InfoWorker()
    controller, _ = _make_controller(d, r, i)
    playlists = [type("P", (), {"status": "queued"})()]

    started = controller.start_run(playlists, "/tmp/out")
    assert started is True
    assert d.started is True


def test_pause_resume_stop_delegate_to_download_worker():
    d = _DownloadWorker()
    r = _RetryWorker()
    i = _InfoWorker()
    controller, _ = _make_controller(d, r, i)
    playlists = [type("P", (), {"status": "queued"})()]
    controller.start_run(playlists, "/tmp/out")

    controller.pause_run()
    controller.resume_run()
    controller.stop_run(wait_ms=1234)

    assert d.paused is True
    assert d.resumed is True
    assert d.stopped is True
    assert d.wait_ms == 1234


def test_retry_worker_cleanup_emits_retry_complete():
    d = _DownloadWorker()
    r = _RetryWorker()
    i = _InfoWorker()
    controller, callbacks = _make_controller(d, r, i)

    controller.retry_videos(object(), [1], "/tmp/out")
    assert r.started is True
    r.completed.emit()
    assert r.deleted is True
    assert callbacks["retry_complete"] == [True]


def test_info_worker_cleanup_on_finished():
    d = _DownloadWorker()
    r = _RetryWorker()
    i = _InfoWorker()
    controller, _ = _make_controller(d, r, i)

    controller.fetch_info_async("pid", "https://x")
    assert i.started is True
    i.finished.emit()
    assert i.deleted is True
