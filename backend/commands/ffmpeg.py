from __future__ import annotations
import math
import sys
import subprocess
import threading
from typing import Callable

from backend.platform.tools import ffmpeg_exe


def probe_duration_sec(path: str) -> int:
    """Return duration of an audio file in seconds using ffprobe."""
    exe = _find_ffmpeg().replace("ffmpeg", "ffprobe")
    try:
        result = subprocess.run(
            [exe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return int(float(result.stdout.strip()))
    except (ValueError, TypeError, subprocess.TimeoutExpired, OSError):
        return 0


def _find_ffmpeg() -> str:
    """Compatibility shim: delegate lookup to platform layer."""
    return ffmpeg_exe()


def ffmpeg_ok() -> bool:
    """Return True if ffmpeg can actually be executed."""
    exe = _find_ffmpeg()
    try:
        r = subprocess.run([exe, "-version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


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
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return False
                on_log(line.rstrip())
            return proc.wait() == 0
        except Exception as exc:
            on_log(f"ffmpeg error: {exc}")
            return False

    def speed(
        self,
        input_path: str,
        output_path: str,
        speed: float,
        on_log: Callable[[str], None],
        stop: threading.Event,
    ) -> bool:
        """Re-encode *input_path* with atempo speed filter to *output_path*.

        For speed > 2.0 chains two identical factors (atempo max is 2.0 per filter).
        """
        if speed > 2.0:
            factor = math.sqrt(speed)
            af = f"atempo={factor:.4f},atempo={factor:.4f}"
        else:
            af = f"atempo={speed:.4f}"

        cmd = [
            _find_ffmpeg(),
            "-i", input_path,
            "-af", af,
            "-codec:a", "libmp3lame",
            "-b:a", "192k",
            "-ac", "1",
            output_path,
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
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return False
                on_log(line.rstrip())
            return proc.wait() == 0
        except Exception as exc:
            on_log(f"ffmpeg error: {exc}")
            return False
