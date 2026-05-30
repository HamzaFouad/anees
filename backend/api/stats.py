"""Playlist statistics and estimates."""
from __future__ import annotations
from backend.models import Playlist
from backend.utils.audio import estimate_size_mb


def playlist_size_estimate(playlist: Playlist) -> float:
    """Return estimated total size in MB for all videos in the playlist."""
    total_sec = sum(v.duration_sec for v in playlist.videos)
    return estimate_size_mb(total_sec)


def playlist_total_duration(playlist: Playlist) -> int:
    """Return total duration in seconds across all videos."""
    return sum(v.duration_sec for v in playlist.videos)
