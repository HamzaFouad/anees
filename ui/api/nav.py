from __future__ import annotations


class NavAPI:
    """Actions that navigate between views."""

    def __init__(self, state) -> None:
        self._state = state

    def go(self, view: str) -> None:
        self._state.set_view(view)

    def go_queue(self)   -> None: self.go("queue")
    def go_history(self) -> None: self.go("history")
    def go_logs(self)    -> None: self.go("logs")
