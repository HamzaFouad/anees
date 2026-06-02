"""Tests for backend/services/splitter_service.py"""
from __future__ import annotations
import os
import threading
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def service():
    """SplitterService with a fully mocked YtdlpClient."""
    with patch("backend.services.splitter_service.YtdlpClient") as MockClient:
        from backend.services.splitter_service import SplitterService
        svc = SplitterService()
        svc._client = MockClient.return_value
        yield svc


# ---------------------------------------------------------------------------
# fetch_playlist_videos
# ---------------------------------------------------------------------------

class TestFetchPlaylistVideos:
    def test_delegates_to_client(self, service):
        expected = [
            ("https://youtu.be/aaa", "Video A", 120),
            ("https://youtu.be/bbb", "Video B", 240),
        ]
        service._client.fetch_video_urls.return_value = expected

        result = service.fetch_playlist_videos("https://youtube.com/playlist?list=PL123")

        service._client.fetch_video_urls.assert_called_once_with(
            "https://youtube.com/playlist?list=PL123"
        )
        assert result == expected

    def test_returns_empty_list_when_client_returns_empty(self, service):
        service._client.fetch_video_urls.return_value = []
        result = service.fetch_playlist_videos("https://youtube.com/playlist?list=PL_EMPTY")
        assert result == []


# ---------------------------------------------------------------------------
# download_clip — happy path
# ---------------------------------------------------------------------------

class TestDownloadClipSuccess:
    def test_creates_dest_dir_and_calls_download(self, service, tmp_path):
        dest = str(tmp_path / "clips")
        mp3_path = os.path.join(dest, "_splitter.mp3")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            # simulate a successful postprocess callback
            os.makedirs(dest, exist_ok=True)
            on_postprocess({
                "status": "finished",
                "info_dict": {"filepath": mp3_path},
            })

        service._client.download.side_effect = fake_download

        # make os.path.exists return True for our mp3
        with patch("os.path.exists", return_value=True):
            result = service.download_clip("https://youtu.be/xyz", dest)

        assert result == mp3_path
        service._client.download.assert_called_once()
        # first positional arg is the url
        assert service._client.download.call_args[0][0] == "https://youtu.be/xyz"

    def test_out_template_uses_splitter_prefix(self, service, tmp_path):
        dest = str(tmp_path / "clips2")
        mp3_path = os.path.join(dest, "_splitter.mp3")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            os.makedirs(dest, exist_ok=True)
            on_postprocess({"status": "finished", "info_dict": {"filepath": mp3_path}})

        service._client.download.side_effect = fake_download

        with patch("os.path.exists", return_value=True):
            service.download_clip("https://youtu.be/abc", dest)

        out_tmpl = service._client.download.call_args[0][1]
        assert "_splitter" in os.path.basename(out_tmpl)


# ---------------------------------------------------------------------------
# download_clip — mkdir failure
# ---------------------------------------------------------------------------

class TestDownloadClipMkdirFailure:
    def test_raises_runtime_error_on_oserror(self, service, tmp_path):
        dest = str(tmp_path / "no_permission")

        with patch("backend.services.splitter_service.Path") as MockPath:
            MockPath.return_value.mkdir.side_effect = OSError("Permission denied")
            with pytest.raises(RuntimeError, match="Cannot create splitter folder"):
                service.download_clip("https://youtu.be/xyz", dest)

    def test_download_not_called_when_mkdir_fails(self, service, tmp_path):
        dest = str(tmp_path / "no_permission2")

        with patch("backend.services.splitter_service.Path") as MockPath:
            MockPath.return_value.mkdir.side_effect = OSError("read-only filesystem")
            try:
                service.download_clip("https://youtu.be/xyz", dest)
            except RuntimeError:
                pass
            service._client.download.assert_not_called()


# ---------------------------------------------------------------------------
# download_clip — stop event
# ---------------------------------------------------------------------------

class TestDownloadClipStopped:
    def test_raises_runtime_error_when_stop_is_set(self, service, tmp_path):
        dest = str(tmp_path / "stopped")
        stop = threading.Event()

        def fake_download(url, out_tmpl, on_progress, on_postprocess, _stop, pause):
            os.makedirs(dest, exist_ok=True)
            _stop.set()  # signal stop during download

        service._client.download.side_effect = fake_download

        with pytest.raises(RuntimeError, match="stopped"):
            service.download_clip("https://youtu.be/xyz", dest, stop=stop)

    def test_stop_error_message_is_exact(self, service, tmp_path):
        dest = str(tmp_path / "stopped2")
        stop = threading.Event()

        def fake_download(url, out_tmpl, on_progress, on_postprocess, _stop, pause):
            os.makedirs(dest, exist_ok=True)
            _stop.set()

        service._client.download.side_effect = fake_download

        with pytest.raises(RuntimeError) as exc_info:
            service.download_clip("https://youtu.be/xyz", dest, stop=stop)
        assert "Splitter download stopped" in str(exc_info.value)


# ---------------------------------------------------------------------------
# download_clip — no MP3 found (no fallback match either)
# ---------------------------------------------------------------------------

class TestDownloadClipNoMp3:
    def test_raises_when_no_mp3_and_no_fallback(self, service, tmp_path):
        dest = str(tmp_path / "empty_dl")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            os.makedirs(dest, exist_ok=True)
            # postprocess called but with non-mp3 extension
            on_postprocess({"status": "finished", "info_dict": {"filepath": "output.webm"}})

        service._client.download.side_effect = fake_download

        with pytest.raises(RuntimeError, match="no MP3"):
            service.download_clip("https://youtu.be/xyz", dest)

    def test_raises_when_postprocess_status_not_finished(self, service, tmp_path):
        dest = str(tmp_path / "not_finished")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            os.makedirs(dest, exist_ok=True)
            on_postprocess({"status": "downloading", "info_dict": {"filepath": "clip.mp3"}})

        service._client.download.side_effect = fake_download

        with pytest.raises(RuntimeError, match="no MP3"):
            service.download_clip("https://youtu.be/xyz", dest)


# ---------------------------------------------------------------------------
# download_clip — fallback glob finds _splitter*.mp3
# ---------------------------------------------------------------------------

class TestDownloadClipFallback:
    def test_fallback_glob_finds_splitter_mp3(self, service, tmp_path):
        dest = str(tmp_path / "fallback")
        os.makedirs(dest, exist_ok=True)
        fallback_file = "_splitter_video_title.mp3"
        (tmp_path / "fallback" / fallback_file).write_text("fake mp3 data")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            # postprocess never appends to downloaded (e.g. filepath missing)
            on_postprocess({"status": "finished", "info_dict": {}})

        service._client.download.side_effect = fake_download

        result = service.download_clip("https://youtu.be/xyz", dest)

        assert result == os.path.join(dest, fallback_file)

    def test_fallback_ignores_non_splitter_files(self, service, tmp_path):
        dest = str(tmp_path / "fallback2")
        os.makedirs(dest, exist_ok=True)
        (tmp_path / "fallback2" / "other_video.mp3").write_text("fake")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            on_postprocess({"status": "finished", "info_dict": {}})

        service._client.download.side_effect = fake_download

        with pytest.raises(RuntimeError, match="no MP3"):
            service.download_clip("https://youtu.be/xyz", dest)

    def test_fallback_first_match_returned(self, service, tmp_path):
        dest = str(tmp_path / "fallback3")
        os.makedirs(dest, exist_ok=True)
        # create two matching files; only one should be returned
        (tmp_path / "fallback3" / "_splitter_a.mp3").write_text("a")
        (tmp_path / "fallback3" / "_splitter_b.mp3").write_text("b")

        def fake_download(url, out_tmpl, on_progress, on_postprocess, stop, pause):
            on_postprocess({"status": "finished", "info_dict": {}})

        service._client.download.side_effect = fake_download

        result = service.download_clip("https://youtu.be/xyz", dest)

        assert result.startswith(dest)
        assert os.path.basename(result).startswith("_splitter")
        assert result.endswith(".mp3")
