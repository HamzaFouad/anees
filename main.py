import sys
import traceback
from pathlib import Path
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
    sys.excepthook = _excepthook

    # verify critical dependencies at startup
    try:
        import yt_dlp
        print(f"[startup] yt-dlp {yt_dlp.version.__version__}", flush=True)
    except ImportError:
        print("[startup] ERROR: yt-dlp not found — run: pip install yt-dlp", flush=True)
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("Anees")
    _icon = Path(__file__).parent / "ui" / "images" / "anees.ico"
    if _icon.exists():
        app.setWindowIcon(QIcon(str(_icon)))
    apply_global_stylesheet(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
