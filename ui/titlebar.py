from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray

from ui.theme import PRIMARY, FG, FG_MUTED, BG, BORDER, WIN_CLOSE_HOVER, ON_PRIMARY, TEXT_MD, EQUALIZER_SVG


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self.setStyleSheet(f"background:{BG};")
        self._drag_pos = QPoint()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(8)

        # app mark
        self._mark = _AppMark()
        lay.addWidget(self._mark)

        # title
        self._title_lbl = QLabel("Anees")
        self._title_lbl.setStyleSheet(
            f"font-size:{TEXT_MD}px; font-weight:600; color:{FG};"
        )
        lay.addWidget(self._title_lbl)

        # subtitle
        self._sub_lbl = QLabel("")
        self._sub_lbl.setStyleSheet(
            f"font-size:{TEXT_MD}px; color:{FG_MUTED};"
        )
        lay.addWidget(self._sub_lbl)

        lay.addStretch()

        # window controls
        for label, close in [("–", False), ("□", False), ("✕", True)]:
            btn = _WinBtn(label, is_close=close)
            lay.addWidget(btn)
            if label == "–":
                btn.clicked.connect(lambda: self.window().showMinimized())
            elif label == "□":
                btn.clicked.connect(self._toggle_max)
            else:
                btn.clicked.connect(self.window().close)

        lay.setSpacing(0)

    def set_subtitle(self, text: str):
        self._sub_lbl.setText(f"— {text}" if text else "")

    def _toggle_max(self):
        w = self.window()
        if w.isMaximized():
            w.showNormal()
        else:
            w.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)


class _AppMark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self._renderer = QSvgRenderer(QByteArray(EQUALIZER_SVG.encode()))

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(PRIMARY))
        p.drawRoundedRect(0, 0, 18, 18, 3, 3)
        self._renderer.render(p, self.rect())


class _WinBtn(QPushButton):
    def __init__(self, label: str, is_close: bool = False, parent=None):
        super().__init__(label, parent)
        self._close = is_close
        self.setFixedSize(46, 36)
        self.setCursor(Qt.ArrowCursor)
        self._set_style(False)

    def _set_style(self, hovered: bool):
        if self._close and hovered:
            bg, fg = WIN_CLOSE_HOVER, ON_PRIMARY
        elif hovered:
            bg, fg = BORDER, FG
        else:
            bg, fg = "transparent", FG_MUTED
        self.setStyleSheet(
            f"QPushButton {{ background:{bg}; color:{fg}; border:none; "
            f"font-size:12px; font-family:'Segoe UI',sans-serif; }}"
        )

    def enterEvent(self, event):
        self._set_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_style(False)
        super().leaveEvent(event)
