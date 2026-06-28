from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor
from ui.components.spinner import Spinner


def _parse_qcolor(css: str) -> QColor:
    """Parse hex or CSS rgba(r,g,b,a) string into QColor."""
    s = css.strip()
    if s.startswith("rgba("):
        parts = s[5:].rstrip(")").split(",")
        r, g, b = int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())
        a = int(float(parts[3].strip()) * 255)
        return QColor(r, g, b, a)
    return QColor(s)


class Chip(QWidget):
    """Pill-shaped chip with an optional leading 6 px dot.

    Background drawn via paintEvent — bypasses Qt QSS border-radius cascade.
    """

    def __init__(self, text: str, bg: str, fg: str,
                 dot: str | None = None,
                 pulse: bool = False,
                 compact: bool = False,
                 variant: str = "badge",
                 tooltip: str = "",
                 parent=None):
        super().__init__(parent)
        self._bg = _parse_qcolor(bg)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if tooltip:
            self.setToolTip(tooltip)

        # pipeline chips: 0 11px padding, 12px font, 26px height
        # badge chips: 2px 8px padding, 11px font (compact: 4px, 10px)
        if variant == "pipeline":
            h_pad, v_pad, fs = 11, 0, 12
            self.setFixedHeight(26)
        elif compact:
            h_pad, v_pad, fs = 4, 2, 10
        else:
            h_pad, v_pad, fs = 8, 2, 11

        lay = QHBoxLayout(self)
        lay.setContentsMargins(h_pad, v_pad, h_pad, v_pad)
        lay.setSpacing(4)

        if dot:
            if pulse:
                dot_w = Spinner(12, dot)
            else:
                dot_w = QLabel()
                dot_w.setFixedSize(6, 6)
                dot_w.setStyleSheet(f"background:{dot}; border-radius:3px; border:none;")
            lay.addWidget(dot_w)

        self._lbl = QLabel(text)
        self._lbl.setTextFormat(Qt.PlainText)
        self._lbl.setStyleSheet(
            f"color:{fg}; font-size:{fs}px; font-weight:600; "
            "background:transparent; border:none; text-decoration:none;"
        )
        lay.addWidget(self._lbl)

    @property
    def label(self) -> QLabel:
        """Inner QLabel — used by PipelineStrip to update count text in-place."""
        return self._lbl

    def stop_animations(self) -> None:
        for sp in self.findChildren(Spinner):
            sp.stop()
        self.hide()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg)
        r = self.height() / 2
        p.drawRoundedRect(self.rect(), r, r)
