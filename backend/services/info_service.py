from __future__ import annotations
from backend.models import Video
from backend.commands.ytdlp import YtdlpClient


class InfoService:
    """Fetch playlist metadata without downloading."""

    def fetch_playlist(self, url: str) -> tuple[list[Video], str]:
        """Return (videos, playlist_title) for the given playlist URL."""
        return YtdlpClient().fetch_info(url)
