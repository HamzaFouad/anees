"""Tests for backend/commands/ytdlp.py — YtdlpClient."""
from __future__ import annotations

import threading
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from backend.commands.ytdlp import YtdlpClient
from backend.models import Video


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(title: str = "My Video", duration: int = 120, url: str = "https://www.youtube.com/watch?v=abc") -> dict:
    return {"title": title, "duration": duration, "webpage_url": url, "url": url}


def _ydl_cm(info: dict) -> MagicMock:
    """Return a mock that behaves as a yt_dlp.YoutubeDL context manager."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.extract_info = MagicMock(return_value=info)
    cm.download = MagicMock()
    return cm


# ---------------------------------------------------------------------------
# fetch_info
# ---------------------------------------------------------------------------

class TestFetchInfo:
    def test_returns_videos_and_title(self):
        entries = [
            _make_entry("Video A", 60),
            _make_entry("Video B", 90),
        ]
        info = {"title": "My Playlist", "entries": entries}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            videos, title = client.fetch_info("https://www.youtube.com/playlist?list=X")

        assert title == "My Playlist"
        assert len(videos) == 2
        assert all(isinstance(v, Video) for v in videos)
        assert videos[0].title == "Video A"
        assert videos[0].duration_sec == 60
        assert videos[0].stage == "queued"
        assert videos[1].title == "Video B"
        assert videos[1].duration_sec == 90

    def test_empty_entries_returns_empty_list_and_blank_title(self):
        info = {"title": "", "entries": []}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            videos, title = client.fetch_info("https://www.youtube.com/playlist?list=X")

        assert videos == []
        assert title == ""

    def test_none_entries_returns_empty_list(self):
        info = {"title": "Sparse", "entries": None}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            videos, title = client.fetch_info("https://www.youtube.com/playlist?list=X")

        assert videos == []
        assert title == "Sparse"

    def test_exception_wraps_in_runtime_error(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.extract_info = MagicMock(side_effect=ValueError("network error"))

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            with pytest.raises(RuntimeError, match="fetch_info failed"):
                client.fetch_info("https://www.youtube.com/playlist?list=X")

    def test_entry_with_missing_title_gets_fallback(self):
        entries = [{"title": None, "duration": 30}]
        info = {"title": "P", "entries": entries}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            videos, _ = client.fetch_info("https://www.youtube.com/playlist?list=X")

        assert videos[0].title == "Video 1"

    def test_entry_with_missing_duration_defaults_to_zero(self):
        entries = [{"title": "Short", "duration": None}]
        info = {"title": "P", "entries": entries}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            videos, _ = client.fetch_info("https://www.youtube.com/playlist?list=X")

        assert videos[0].duration_sec == 0


# ---------------------------------------------------------------------------
# fetch_video_urls
# ---------------------------------------------------------------------------

class TestFetchVideoUrls:
    def test_returns_url_title_duration_tuples(self):
        entries = [
            {"webpage_url": "https://www.youtube.com/watch?v=aaa", "title": "Alpha", "duration": 60},
            {"webpage_url": "https://www.youtube.com/watch?v=bbb", "title": "Beta",  "duration": 90},
        ]
        info = {"entries": entries}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            result = client.fetch_video_urls("https://www.youtube.com/playlist?list=X")

        assert len(result) == 2
        assert result[0] == ("https://www.youtube.com/watch?v=aaa", "Alpha", 60)
        assert result[1] == ("https://www.youtube.com/watch?v=bbb", "Beta", 90)

    def test_short_url_gets_prefixed(self):
        """An entry whose url has no http scheme must get the youtube.com/watch prefix."""
        entries = [{"url": "abc123", "webpage_url": None, "title": "Short", "duration": 30}]
        info = {"entries": entries}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            result = client.fetch_video_urls("https://www.youtube.com/playlist?list=X")

        assert result[0][0] == "https://www.youtube.com/watch?v=abc123"

    def test_exception_wraps_in_runtime_error(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.extract_info = MagicMock(side_effect=ConnectionError("timeout"))

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            with pytest.raises(RuntimeError, match="fetch_video_urls failed"):
                client.fetch_video_urls("https://www.youtube.com/playlist?list=X")

    def test_none_entries_returns_empty_list(self):
        info = {"entries": None}
        cm = _ydl_cm(info)

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            client = YtdlpClient()
            result = client.fetch_video_urls("https://www.youtube.com/playlist?list=X")

        assert result == []


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

class TestDownload:
    def _run_download(
        self,
        cm: MagicMock,
        *,
        stop: threading.Event | None = None,
        pause: threading.Event | None = None,
        on_progress=None,
        on_postprocess=None,
        on_log=None,
        playlist_items: str | None = None,
    ) -> dict:
        """Helper: patch YoutubeDL and run download, return the opts that were passed."""
        captured_opts: dict = {}
        original_init = cm.__class__

        def _capture(opts):
            captured_opts.update(opts)
            return cm

        if stop is None:
            stop = threading.Event()
        if pause is None:
            pause = threading.Event()
            pause.set()  # not paused by default
        if on_progress is None:
            on_progress = MagicMock()
        if on_postprocess is None:
            on_postprocess = MagicMock()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/%(title)s.%(ext)s",
                on_progress=on_progress,
                on_postprocess=on_postprocess,
                stop=stop,
                pause=pause,
                on_log=on_log,
                playlist_items=playlist_items,
            )
        return captured_opts

    def test_download_calls_ydl_download(self):
        cm = _ydl_cm({})
        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/%(title)s.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
            )

        cm.download.assert_called_once_with(["https://www.youtube.com/watch?v=XYZ"])

    def test_download_cancelled_is_swallowed(self):
        import yt_dlp.utils

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock(side_effect=yt_dlp.utils.DownloadCancelled("stopped"))

        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            # must NOT raise
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/out.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
            )

    def test_other_exceptions_are_reraised(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock(side_effect=OSError("disk full"))

        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            with pytest.raises(OSError, match="disk full"):
                YtdlpClient().download(
                    url="https://www.youtube.com/watch?v=XYZ",
                    output_template="/tmp/out.%(ext)s",
                    on_progress=MagicMock(),
                    on_postprocess=MagicMock(),
                    stop=threading.Event(),
                    pause=pause,
                )

    def test_other_exception_calls_on_log_error(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock(side_effect=OSError("disk full"))

        pause = threading.Event()
        pause.set()
        on_log = MagicMock()

        with patch("yt_dlp.YoutubeDL", return_value=cm):
            with pytest.raises(OSError):
                YtdlpClient().download(
                    url="https://www.youtube.com/watch?v=XYZ",
                    output_template="/tmp/out.%(ext)s",
                    on_progress=MagicMock(),
                    on_postprocess=MagicMock(),
                    stop=threading.Event(),
                    pause=pause,
                    on_log=on_log,
                )

        on_log.assert_called_once()
        level, msg = on_log.call_args[0]
        assert level == "error"
        assert "disk full" in msg

    def test_playlist_items_passed_to_opts(self):
        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/playlist?list=X",
                output_template="/tmp/out.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
                playlist_items="1,3,5",
            )

        assert captured.get("playlist_items") == "1,3,5"

    def test_playlist_items_absent_when_not_provided(self):
        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/out.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
            )

        assert "playlist_items" not in captured

    def test_progress_hook_wired(self):
        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        pause = threading.Event()
        pause.set()
        on_progress = MagicMock()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/out.%(ext)s",
                on_progress=on_progress,
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
            )

        hooks = captured.get("progress_hooks", [])
        assert len(hooks) == 1
        # calling the hook should propagate to on_progress
        hooks[0]({"status": "downloading"})
        on_progress.assert_called_once_with({"status": "downloading"})

    def test_postprocessor_hook_wired(self):
        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        pause = threading.Event()
        pause.set()
        on_postprocess = MagicMock()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/out.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=on_postprocess,
                stop=threading.Event(),
                pause=pause,
            )

        pp_hooks = captured.get("postprocessor_hooks", [])
        assert len(pp_hooks) == 1
        assert pp_hooks[0] is on_postprocess

    def test_progress_hook_raises_download_cancelled_when_stop_set(self):
        import yt_dlp.utils

        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        stop = threading.Event()
        stop.set()
        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/out.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=stop,
                pause=pause,
            )

        hook = captured["progress_hooks"][0]
        with pytest.raises(yt_dlp.utils.DownloadCancelled):
            hook({"status": "downloading"})

    def test_output_template_passed_to_opts(self):
        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/downloads/%(title)s.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
            )

        assert captured["outtmpl"] == "/downloads/%(title)s.%(ext)s"

    def test_mp3_postprocessor_configured(self):
        captured: dict = {}

        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.download = MagicMock()

        def _capture(opts):
            captured.update(opts)
            return cm

        pause = threading.Event()
        pause.set()

        with patch("yt_dlp.YoutubeDL", side_effect=_capture):
            YtdlpClient().download(
                url="https://www.youtube.com/watch?v=XYZ",
                output_template="/tmp/out.%(ext)s",
                on_progress=MagicMock(),
                on_postprocess=MagicMock(),
                stop=threading.Event(),
                pause=pause,
            )

        pps = captured.get("postprocessors", [])
        assert len(pps) == 1
        assert pps[0]["key"] == "FFmpegExtractAudio"
        assert pps[0]["preferredcodec"] == "mp3"
        assert pps[0]["preferredquality"] == "192"
        # mono: -ac 1 passed via postprocessor_args
        pp_args = captured.get("postprocessor_args", {})
        assert "-ac" in pp_args.get("ffmpegextractaudio", [])
        assert "1" in pp_args.get("ffmpegextractaudio", [])
