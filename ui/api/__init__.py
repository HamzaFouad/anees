"""ui/api — all UI action methods in one place.

Panels, dialogs, and chrome call these instead of touching AppState directly.
Every mutation goes through here; read-only access (state.playlists, signals)
still comes from AppState directly.

Usage:
    api = UIApi(state)
    api.run.start()
    api.queue.add(pl)
    api.nav.go_queue()
"""

from ui.api.run import RunAPI
from ui.api.queue import QueueAPI
from ui.api.nav import NavAPI

__all__ = ["UIApi", "RunAPI", "QueueAPI", "NavAPI"]


class UIApi:
    """Convenience wrapper — groups all API objects under one handle."""

    def __init__(self, state) -> None:
        self.run   = RunAPI(state)
        self.queue = QueueAPI(state)
        self.nav   = NavAPI(state)
