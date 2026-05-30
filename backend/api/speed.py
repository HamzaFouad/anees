from __future__ import annotations
import threading

from backend.services.speed_service import SpeedService


class SpeedAPI:
    def apply_speed(
        self,
        paths: list[str],
        speed: float,
        stop: threading.Event | None = None,
        on_log=None,
    ) -> list[str]:
        return SpeedService(on_log=on_log).apply_speed(paths, speed, stop)
