from __future__ import annotations
import subprocess
import sys
import threading
from typing import Callable

_NO_WINDOW = 0x08000000  # Windows CREATE_NO_WINDOW


class CommandRunner:
    def __init__(self):
        self._proc: subprocess.Popen | None = None
        self._stopped = threading.Event()
        self._paused  = threading.Event()
        self._paused.set()  # not paused initially

    def run(
        self,
        cmd: list[str],
        on_line: Callable[[str], None],
        on_done: Callable[[int], None],
    ) -> None:
        self._stopped.clear()
        kwargs: dict = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if sys.platform == "win32":
            kwargs["creationflags"] = _NO_WINDOW

        self._proc = subprocess.Popen(cmd, **kwargs)

        for raw in self._proc.stdout:
            self._paused.wait()           # block while paused
            if self._stopped.is_set():
                break
            on_line(raw.rstrip())

        if self._stopped.is_set() and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

        on_done(self._proc.wait())

    def stop(self) -> None:
        self._stopped.set()
        self._paused.set()          # unblock if paused so the loop can exit
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def pause(self) -> None:
        self._paused.clear()

    def resume(self) -> None:
        self._paused.set()
