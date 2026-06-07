import os
import sys
import threading
import traceback
from pathlib import Path


def _filter_macos_stderr() -> None:
    """Intercept fd 2 and drop noisy macOS system messages.

    TSMSendMessageToUIServer is written by the macOS Text Services Manager
    directly to the stderr file descriptor — Python-level sys.stderr filtering
    cannot catch it.  We replace fd 2 with a pipe and drain it on a daemon
    thread, forwarding every line except known OS noise.
    """
    if sys.platform != "darwin":
        return

    _NOISE = (
        "TSMSendMessageToUIServer",
        "CFMessagePortSendRequest",
    )

    r_fd, w_fd = os.pipe()
    real_stderr = os.dup(2)   # save the original fd 2
    os.dup2(w_fd, 2)          # redirect fd 2 → write-end of pipe
    os.close(w_fd)

    def _drain() -> None:
        with os.fdopen(r_fd, "r", errors="replace") as pipe_r:
            for line in pipe_r:
                if not any(token in line for token in _NOISE):
                    os.write(real_stderr, line.encode("utf-8", errors="replace"))

    threading.Thread(target=_drain, daemon=True, name="stderr-filter").start()
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.theme import apply_global_stylesheet
from ui.main_window import MainWindow


def _excepthook(exc_type, exc_value, exc_tb):
    print("\n[UNCAUGHT EXCEPTION]", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.stdout.flush()
    sys.stderr.flush()


def main():
    _filter_macos_stderr()
    sys.excepthook = _excepthook

    # verify critical dependencies at startup
    try:
        import yt_dlp
        print(f"[startup] yt-dlp {yt_dlp.version.__version__}", flush=True)
    except ImportError:
        print("[startup] ERROR: yt-dlp not found — run: pip install yt-dlp", flush=True)
        sys.exit(1)

    # Windows: set AUMID before creating QApplication so the taskbar groups the
    # app under its own identity (not under the Python interpreter's icon).
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ai.ginni.anees")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Anees")

    # Resolve the icon path whether running from source or a PyInstaller bundle.
    if getattr(sys, "frozen", False):
        _icon = Path(sys._MEIPASS) / "images" / "anees.ico"  # type: ignore[attr-defined]
    else:
        _icon = Path(__file__).parent / "ui" / "images" / "anees.ico"
    _qicon = QIcon(str(_icon)) if _icon.exists() else QIcon()
    app.setWindowIcon(_qicon)

    apply_global_stylesheet(app)

    from backend.api.health import ffmpeg_ok
    if not ffmpeg_ok():
        from ui.dialogs.ffmpeg_missing import FfmpegMissingDialog
        FfmpegMissingDialog().exec()
        sys.exit(1)

    window = MainWindow()
    window.setWindowIcon(_qicon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
