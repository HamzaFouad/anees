from __future__ import annotations
from backend.models import Video
from backend.commands.ytdlp import YtdlpClient


class InfoService:
    """Fetch playlist metadata without downloading."""

    def __init__(self, client: YtdlpClient | None = None):
        self._client = client or YtdlpClient()

    def fetch_playlist(self, url: str) -> tuple[list[Video], str]:
        """Return (videos, playlist_title) for the given playlist URL."""
        return self._client.fetch_info(url)
