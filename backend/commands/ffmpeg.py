from __future__ import annotations
import os
import sys
import subprocess
import threading
from typing import Callable


def _find_ffmpeg() -> str:
    """Return the ffmpeg binary path — bundled first, then PATH."""
    if getattr(sys, "frozen", False):
        name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        path = os.path.join(sys._MEIPASS, name)  # type: ignore[attr-defined]
        if os.path.exists(path):
            return path
    return "ffmpeg"


class FfmpegClient:
    """Thin wrapper around the ffmpeg binary for post-processing operations."""

    def split(
        self,
        input_path: str,
        output_pattern: str,
        chunk_seconds: int,
        on_log: Callable[[str], None],
        stop: threading.Event,
    ) -> bool:
        """Split *input_path* into fixed-length chunks using stream copy.

        *output_pattern* should contain a printf-style counter,
        e.g. ``/path/to/file_part%03d.mp3``.

        Returns True on success, False if ffmpeg returned non-zero or was stopped.
        """
        cmd = [
            _find_ffmpeg(),
            "-i", input_path,
            "-f", "segment",
            "-segment_time", str(chunk_seconds),
            "-c", "copy",
            "-reset_timestamps", "1",
            output_pattern,
            "-y",
        ]

        kwargs: dict = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000   # CREATE_NO_WINDOW

        try:
            proc = subprocess.Popen(cmd, **kwargs)
            for line in proc.stdout:
                if stop.is_set():
                    proc.terminate()
                    proc.wait(timeout=5)
                    return False
                on_log(line.rstrip())
            return proc.wait() == 0
        except Exception as exc:
            on_log(f"ffmpeg error: {exc}")
            return False
