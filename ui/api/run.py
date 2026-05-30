from __future__ import annotations
from backend.models import RunState


class RunAPI:
    """Actions that control the download run lifecycle."""

    def __init__(self, state) -> None:
        self._state = state

    def start(self)  -> None: self._state.set_run_state(RunState.RUNNING)
    def pause(self)  -> None: self._state.set_run_state(RunState.PAUSED)
    def resume(self) -> None: self._state.set_run_state(RunState.RUNNING)
    def stop(self)   -> None: self._state.set_run_state(RunState.IDLE)
