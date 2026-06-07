from __future__ import annotations
import os
import threading
from typing import Callable

from backend.commands.ffmpeg import FfmpegClient
from backend.errors import InvalidOutputFolderError


class SpeedService:
    def __init__(
        self,
        on_log: Callable[[str], None] | None = None,
        client: FfmpegClient | None = None,
    ):
        self._client = client or FfmpegClient()
        self._on_log = on_log or (lambda _: None)

    def apply_speed(
        self,
        paths: list[str],
        speed: float,
        stop: threading.Event | None = None,
    ) -> list[str]:
        """Apply atempo speed filter to each file in *paths* in-place.

        Files are written to a temp path and atomically renamed on success.
        Returns the same list of paths (originals replaced by sped-up versions).
        """
        if stop is None:
            stop = threading.Event()

        for path in paths:
            if stop.is_set():
                break
            if not os.path.exists(path):
                self._on_log(f"speed: file not found — {path}")
                continue

            tmp = path + ".spd.mp3"
            self._on_log(f"Applying ×{speed} to {os.path.basename(path)}…")

            ok = self._client.speed(path, tmp, speed, self._on_log, stop)

            if ok and os.path.exists(tmp):
                try:
                    os.replace(tmp, path)
                except OSError as exc:
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                    raise InvalidOutputFolderError(
                        technical_message=f"Speed: cannot replace file — {exc}"
                    ) from exc
            else:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                if not stop.is_set():
                    self._on_log(f"speed: failed for {os.path.basename(path)} — keeping original")

        return paths
