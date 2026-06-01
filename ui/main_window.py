from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPainterPath

from ui.state import AppState
from ui.titlebar import TitleBar
from ui.toolbar import Toolbar
from ui.tabs import TabBar
from ui.statusbar import StatusBar
from ui.panels.queue_list import QueueList
from ui.panels.detail import DetailPanel
from ui.panels.history import HistoryPanel
from ui.panels.console import ConsolePanel, ConsoleToggleBar


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._state = AppState()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(1100, 720)
        self.resize(1100, 720)
        self.setObjectName("mainWindow")
        from ui.theme import BG
        self._bg_color = QColor(BG)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # title bar
        self._titlebar = TitleBar(self)
        root.addWidget(self._titlebar)

        # toolbar
        self._toolbar = Toolbar(self._state, self)
        self._toolbar.add_clicked.connect(self._on_add)
        self._toolbar.settings_clicked.connect(self._on_settings)
        self._toolbar.about_clicked.connect(self._on_about)
        root.addWidget(self._toolbar)

        # tabs
        self._tabs = TabBar(self._state, self)
        root.addWidget(self._tabs)

        # main content area
        self._content = QStackedWidget()
        root.addWidget(self._content, 1)

        # queue view (left sidebar + detail)
        self._queue_view = QWidget()
        q_lay = QHBoxLayout(self._queue_view)
        q_lay.setContentsMargins(0, 0, 0, 0)
        q_lay.setSpacing(0)
        self._queue_list = QueueList(self._state)
        q_lay.addWidget(self._queue_list)
        from ui.theme import BORDER
        vsep = QFrame()
        vsep.setFixedWidth(1)
        vsep.setStyleSheet(f"background:{BORDER}; border:none;")
        q_lay.addWidget(vsep)
        self._detail = DetailPanel(self._state)
        q_lay.addWidget(self._detail, 1)
        self._content.addWidget(self._queue_view)

        # history view
        self._history = HistoryPanel()
        self._history.rerun_requested.connect(self._on_rerun)
        self._content.addWidget(self._history)

        # global console (full-width; outside tab content)
        self._console = ConsolePanel(self._state, self)
        self._console_toggle = ConsoleToggleBar(self._console, self)
        root.addWidget(self._console)
        root.addWidget(self._console_toggle)

        # full-width separator + status bar
        from ui.theme import BORDER
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        root.addWidget(sep)
        root.addWidget(StatusBar(self))

        # wire view switching
        self._state.view_changed.connect(self._on_view)
        self._on_view(self._state.view)

    def _on_view(self, view: str):
        idx = {"queue": 0, "history": 1}.get(view, 0)
        self._content.setCurrentIndex(idx)

    def _on_add(self):
        if not self._state.locked:
            from ui.dialogs.add_playlist import AddPlaylistDialog
            AddPlaylistDialog(self._state, self).exec()

    def _on_settings(self):
        from ui.dialogs.settings import SettingsDialog
        SettingsDialog(self._state, self).exec()

    def _on_about(self):
        from ui.dialogs.about import AboutDialog
        AboutDialog(self).exec()

    def _on_rerun(self):
        from ui.api import NavAPI
        NavAPI(self._state).go_queue()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_color)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 12, 12)
        p.drawPath(path)

