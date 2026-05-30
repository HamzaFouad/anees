from __future__ import annotations
from backend.models import Playlist


class QueueAPI:
    """Actions on the playlist queue."""

    def __init__(self, state) -> None:
        self._state = state

    def add(self, playlist: Playlist) -> None:
        self._state.add_playlist(playlist)

    def remove(self, playlist_id: str) -> None:
        self._state.remove_playlist(playlist_id)

    def select(self, playlist_id: str) -> None:
        self._state.set_selected(playlist_id)

    def search(self, query: str) -> None:
        self._state.set_query(query)
