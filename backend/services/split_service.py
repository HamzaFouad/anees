from __future__ import annotations
import os
import re
import threading
from typing import Callable

from backend.commands.ffmpeg import FfmpegClient


class SplitService:
    def __init__(self, on_log: Callable[[str], None] | None = None):
        self._client = FfmpegClient()
        self._on_log = on_log or (lambda _: None)

    def split_file(
        self,
        input_path: str,
        chunk_min: int,
        stop: threading.Event | None = None,
    ) -> list[str]:
        """Split *input_path* into ``chunk_min``-minute chunks using stream copy.

        Deletes the original file if splitting succeeds.
        Returns a list of the created part paths (or ``[input_path]`` on failure).
        """
        if stop is None:
            stop = threading.Event()

        if not os.path.exists(input_path):
            self._on_log(f"split: file not found — {input_path}")
            return []

        base, _ = os.path.splitext(input_path)
        output_pattern = f"{base}_part%03d.mp3"
        out_dir = os.path.dirname(input_path)

        self._on_log(
            f"Splitting {os.path.basename(input_path)} "
            f"into {chunk_min}-min chunks…"
        )

        ok = self._client.split(
            input_path,
            output_pattern,
            chunk_min * 60,
            self._on_log,
            stop,
        )

        if not ok:
            self._on_log("Split failed or stopped — keeping original file")
            return [input_path]

        # Collect the generated parts in order
        stem = os.path.basename(base)
        parts = sorted(
            os.path.join(out_dir, f)
            for f in os.listdir(out_dir)
            if re.match(rf"^{re.escape(stem)}_part\d+\.mp3$", f)
        )

        if parts:
            self._on_log(f"Split complete: {len(parts)} parts")
            try:
                os.remove(input_path)
            except OSError:
                pass
            return parts

        # ffmpeg succeeded but no parts found — return original
        return [input_path]
