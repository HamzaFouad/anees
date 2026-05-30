"""Split API — ui/ uses this to trigger audio splitting."""
from __future__ import annotations
import threading
from typing import Callable


class SplitAPI:
    def split_file(
        self,
        input_path: str,
        chunk_min: int,
        on_log: Callable[[str], None] | None = None,
        stop: threading.Event | None = None,
    ) -> list[str]:
        from backend.services.split_service import SplitService
        return SplitService(on_log=on_log).split_file(input_path, chunk_min, stop)
