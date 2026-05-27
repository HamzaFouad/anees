from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QFrame,
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QIcon, QFont
from PySide6.QtSvg import QSvgRenderer

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, FG, FG_MUTED, FG_SUBTLE,
    BG, BG_MUTED, BG_ACCENT, BORDER,
    SUCCESS, SUCCESS_DARK, SUCCESS_BG,
    ERROR_DARK, ERROR_BG, ERROR_BORDER,
    WARN_DARK, WARN_BG,
    PIPELINE_STAGES, make_icon_svg, fmt_dur,
)


def icon_pixmap(key: str, size: int, color: str = FG_MUTED) -> QPixmap:
    data = make_icon_svg(key, size, color)
    renderer = QSvgRenderer(data)
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    renderer.render(p)
    p.end()
    return px


def icon_label(key: str, size: int = 14, color: str = FG_MUTED) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(icon_pixmap(key, size, color))
    lbl.setFixedSize(size, size)
    return lbl


# ── Btn ───────────────────────────────────────────────────────────────────────
_BTN_STYLES = {
    "primary":   (PRIMARY,   "#fff",      PRIMARY_HOVER,          "transparent"),
    "outline":   ("#fff",    FG,          BG_ACCENT,              BORDER),
    "secondary": (BG_MUTED,  FG_SUBTLE,   "#E2E8F0",              "transparent"),
    "ghost":     ("transparent", FG,      BG_ACCENT,              "transparent"),
    "danger":    ("#fff",    ERROR_DARK,  ERROR_BG,               BORDER),
}
_BTN_SIZES = {
    "sm": (28, 10, 12),
    "md": (32, 14, 13),
    "lg": (40, 20, 14),
}

class Btn(QPushButton):
    def __init__(self, text: str = "", variant: str = "primary", size: str = "md",
                 icon_key: str = "", parent=None):
        super().__init__(parent)
        bg, fg, hover_bg, border = _BTN_STYLES.get(variant, _BTN_STYLES["primary"])
        h, px, fs = _BTN_SIZES.get(size, _BTN_SIZES["md"])
        self.setFixedHeight(h)
        self.setCursor(Qt.PointingHandCursor)
        border_css = f"1px solid {border}" if border != "transparent" else "none"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg}; color: {fg};
                border: {border_css}; border-radius: 6px;
                padding: 0 {px}px; font-size: {fs}px; font-weight: 500;
                text-align: center;
            }}
            QPushButton:hover {{ background: {hover_bg}; }}
            QPushButton:disabled {{
                background: #F3F4F6; color: {FG_MUTED};
                border: 1px solid {BORDER}; opacity: 0.6;
            }}
        """)
        if icon_key:
            px_map = icon_pixmap(icon_key, fs, fg)
            self.setIcon(QIcon(px_map))
            self.setIconSize(px_map.size())
        if text:
            self.setText(text)


# ── Badge ─────────────────────────────────────────────────────────────────────
_BADGE_STYLES = {
    "default": (BG_MUTED,   FG_SUBTLE),
    "primary": ("rgba(0,68,255,0.10)", PRIMARY),
    "success": (SUCCESS_BG, SUCCESS_DARK),
    "active":  ("rgba(0,68,255,0.10)", PRIMARY),
    "queued":  (WARN_BG,    WARN_DARK),
    "error":   (ERROR_BG,   ERROR_DARK),
    "mono":    (BG_ACCENT,  FG_SUBTLE),
}

class Badge(QLabel):
    def __init__(self, text: str = "", kind: str = "default", parent=None):
        super().__init__(text, parent)
        bg, fg = _BADGE_STYLES.get(kind, _BADGE_STYLES["default"])
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg}; color: {fg};
                border-radius: 4px; padding: 2px 8px;
                font-size: 11px; font-weight: 500;
            }}
        """)
        self.setContentsMargins(0, 0, 0, 0)


# ── Toggle ────────────────────────────────────────────────────────────────────
class Toggle(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(34, 20)
        self.setCursor(Qt.PointingHandCursor)

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, v: bool):
        self._checked = v
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        # track
        p.setBrush(QColor(PRIMARY if self._checked else "#D1D5DB"))
        p.drawRoundedRect(0, 3, 34, 14, 7, 7)
        # thumb
        p.setBrush(QColor("white"))
        x = 18 if self._checked else 2
        p.drawEllipse(x, 2, 16, 16)

    def mousePressEvent(self, _event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()


# ── SlimProgressBar ───────────────────────────────────────────────────────────
class SlimProgressBar(QWidget):
    def __init__(self, color: str = PRIMARY, track: str = "#E5E7EB",
                 bar_height: int = 4, parent=None):
        super().__init__(parent)
        self._value = 0
        self._total = 100
        self._color = color
        self._track = track
        self._h = bar_height
        self.setFixedHeight(bar_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_value(self, value: int, total: int = 100):
        self._value = value
        self._total = total
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        r = self._h // 2
        p.setBrush(QColor(self._track))
        p.drawRoundedRect(0, 0, self.width(), self._h, r, r)
        if self._total > 0 and self._value > 0:
            w = max(r * 2, int(self.width() * min(1.0, self._value / self._total)))
            p.setBrush(QColor(self._color))
            p.drawRoundedRect(0, 0, w, self._h, r, r)


# ── PipelineStrip ─────────────────────────────────────────────────────────────
class PipelineStrip(QWidget):
    def __init__(self, active_stage: str = "download",
                 split_enabled: bool = True, compact: bool = False, parent=None):
        super().__init__(parent)
        self._active = active_stage
        self._split = split_enabled
        self._compact = compact
        self._build()

    def _stage_index(self, key: str) -> int:
        for i, (k, *_) in enumerate(PIPELINE_STAGES):
            if k == key:
                return i
        return -1

    def _build(self):
        # clear
        for child in self.findChildren(QWidget):
            child.deleteLater()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4 if self._compact else 6)

        ai = 99 if self._active == "done" else self._stage_index(self._active)
        stages = [(k, lbl, short, ico) for k, lbl, short, ico in PIPELINE_STAGES
                  if self._split or k != "split"]

        for i, (key, label, short, _) in enumerate(stages):
            is_done   = ai > i or self._active == "done"
            is_active = ai == i

            if is_done:
                bg, fg, dot = SUCCESS_BG, SUCCESS_DARK, SUCCESS
            elif is_active:
                bg, fg, dot = "rgba(0,68,255,0.10)", PRIMARY, PRIMARY
            else:
                bg, fg, dot = BG_ACCENT, FG_MUTED, BORDER

            pill = QWidget()
            pill.setToolTip(label)
            pl = QHBoxLayout(pill)
            pl.setContentsMargins(4 if self._compact else 8,
                                  2 if self._compact else 4,
                                  4 if self._compact else 8,
                                  2 if self._compact else 4)
            pl.setSpacing(4)

            dot_w = QLabel()
            dot_w.setFixedSize(6, 6)
            dot_w.setStyleSheet(
                f"background:{dot}; border-radius:3px;"
                + (f" border: 3px solid rgba(0,68,255,0.18);" if is_active else "")
            )
            pl.addWidget(dot_w)

            txt = QLabel(short if self._compact else label)
            txt.setStyleSheet(
                f"color:{fg}; font-size:{'10' if self._compact else '11'}px; font-weight:500;"
            )
            pl.addWidget(txt)
            pill.setStyleSheet(f"background:{bg}; border-radius:99px;")
            lay.addWidget(pill)

            if i < len(stages) - 1:
                sep = QFrame()
                sep.setFixedSize(6 if self._compact else 10, 1)
                sep.setStyleSheet(f"background:{BORDER};")
                lay.addWidget(sep)

        lay.addStretch()

    def update_stage(self, active_stage: str, split_enabled: bool):
        self._active = active_stage
        self._split = split_enabled
        self._build()


# ── Field (label wrapper) ─────────────────────────────────────────────────────
class Field(QWidget):
    def __init__(self, label: str, hint: str = "", inline: bool = False, parent=None):
        super().__init__(parent)
        if inline:
            lay = QHBoxLayout(self)
        else:
            lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            f"font-size:11px; font-weight:500; color:{FG_MUTED}; letter-spacing:0.04em;"
        )
        if inline:
            lbl.setFixedWidth(100)
        lay.addWidget(lbl)

        self._content_area = QWidget()
        clay = QVBoxLayout(self._content_area)
        clay.setContentsMargins(0, 0, 0, 0)
        clay.setSpacing(2)
        lay.addWidget(self._content_area)

        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"font-size:11px; color:{FG_MUTED};")
            clay.addWidget(hint_lbl)

    def content_layout(self):
        return self._content_area.layout()


# ── StyledInput ───────────────────────────────────────────────────────────────
class StyledInput(QLineEdit):
    def __init__(self, placeholder: str = "", mono: bool = False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        font_family = "'JetBrains Mono', monospace" if mono else "inherit"
        self.setStyleSheet(f"""
            QLineEdit {{
                height: 32px; padding: 0 10px;
                border: 1px solid {BORDER}; border-radius: 6px;
                font-size: 13px; font-family: {font_family};
                background: {BG}; color: {FG};
            }}
            QLineEdit:focus {{
                border-color: {PRIMARY};
            }}
        """)


# ── Separator ─────────────────────────────────────────────────────────────────
class VSep(QFrame):
    """1px vertical divider for toolbars."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.VLine)
        self.setFixedWidth(1)
        self.setStyleSheet(f"background:{BORDER}; border:none;")


# ── Spinning indicator ────────────────────────────────────────────────────────
class Spinner(QWidget):
    def __init__(self, size: int = 18, color: str = PRIMARY, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._color = color
        self.setFixedSize(size, size)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width()
        pen = QPen(QColor(self._color), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(2, 2, s - 4, s - 4, self._angle * 16, 270 * 16)

    def stop(self):
        self._timer.stop()
