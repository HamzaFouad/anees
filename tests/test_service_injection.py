"""Light DI tests for service constructor injection."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from backend.services.download_service import DownloadService
from backend.services.info_service import InfoService
from backend.services.speed_service import SpeedService
from backend.services.split_service import SplitService


def test_info_service_uses_injected_client():
    client = MagicMock()
    client.fetch_info.return_value = ([], "title")
    svc = InfoService(client=client)
    videos, title = svc.fetch_playlist("https://x")
    assert videos == []
    assert title == "title"
    client.fetch_info.assert_called_once_with("https://x")


def test_split_service_uses_injected_client():
    client = MagicMock()
    client.split.return_value = False
    svc = SplitService(client=client)
    with patch("os.path.exists", return_value=True):
        svc.split_file("/tmp/in.mp3", chunk_min=5)
    client.split.assert_called_once()


def test_speed_service_uses_injected_client():
    client = MagicMock()
    client.speed.return_value = False
    svc = SpeedService(client=client)
    with patch("os.path.exists", return_value=True), patch("os.remove"):
        svc.apply_speed(["/tmp/in.mp3"], speed=1.5)
    client.speed.assert_called_once()


def test_download_service_accepts_injected_dependencies():
    client = MagicMock()
    stop_event = threading.Event()
    pause_event = threading.Event()
    split_factory = MagicMock()
    speed_factory = MagicMock()

    svc = DownloadService(
        client=client,
        stop_event=stop_event,
        pause_event=pause_event,
        split_service_factory=split_factory,
        speed_service_factory=speed_factory,
    )

    assert svc._client is client
    assert svc._stop is stop_event
    assert svc._pause is pause_event
    assert svc._make_split_service is split_factory
    assert svc._make_speed_service is speed_factory
