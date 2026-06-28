from __future__ import annotations
from backend.models import Video


def probe_file_duration(path: str) -> int:
    """Return duration in seconds of a local audio file via ffprobe."""
    from backend.commands.ffmpeg import probe_duration_sec
    return probe_duration_sec(path)


class InfoAPI:
    """Public API for playlist metadata fetching.

    UI workers use this class — never import backend.services directly.
    """

    def fetch_playlist(self, url: str) -> tuple[list[Video], str]:
        """Return (videos, playlist_title) without downloading."""
        from backend.services.info_service import InfoService
        return InfoService().fetch_playlist(url)
