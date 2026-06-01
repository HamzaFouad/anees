from __future__ import annotations
import math
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout,
    QSizePolicy, QFrame, QDialog,
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QIcon, QFont
from PySide6.QtSvg import QSvgRenderer

from ui.theme import (
    PRIMARY, PRIMARY_HOVER, PRIMARY_TINT_8, PRIMARY_TINT_18,
    ON_PRIMARY, SURFACE_ALT, DISABLED_BG, DISABLED_FG,
    FG, FG_MUTED, FG_SUBTLE,
    BG, BG_MUTED, BG_SUBTLE, BG_ACCENT, BORDER,
    SUCCESS, SUCCESS_DARK, SUCCESS_BG,
    ERROR_DARK, ERROR_BG, ERROR_BORDER,
    WARN_DARK, WARN_BG,
    TEXT_XS, TEXT_SM, TEXT_MD,
    SPACE_4, SPACE_8,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_PILL,
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


def section_card_qss(
    object_name: str,
    background: str,
    border: str = BORDER,
    radius: int = RADIUS_LG,
) -> str:
    """Scoped card chrome so children keep control of their own visuals."""
    return (
        f"#{object_name} {{ "
        f"border:1px solid {border}; border-radius:{radius}px; background:{background}; "
        "}"
    )


def make_transparent_row(widget: QWidget) -> None:
    """Rows inside tinted containers should not repaint the base surface."""
    widget.setAttribute(Qt.WA_NoSystemBackground, True)
    widget.setAttribute(Qt.WA_OpaquePaintEvent, False)
    widget.setAutoFillBackground(False)
    widget.setStyleSheet("background:transparent; border:none;")


def hsep(color: str = BORDER, parent=None) -> QFrame:
    sep = QFrame(parent)
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background:{color}; border:none;")
    return sep


# ── Btn ───────────────────────────────────────────────────────────────────────
_BTN_STYLES = {
    "primary":   (PRIMARY,        ON_PRIMARY,  PRIMARY_HOVER,   "transparent"),
    "outline":   (BG,             FG,          BG_ACCENT,       BORDER),
    "secondary": (BG_MUTED,       FG_SUBTLE,   SURFACE_ALT,     "transparent"),
    "ghost":     ("transparent",  FG,          BG_ACCENT,       "transparent"),
    "danger":    (ON_PRIMARY,     ERROR_DARK,  ERROR_BG,        BORDER),
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
                background: {DISABLED_BG}; color: {DISABLED_FG};
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
    "default": (BG_MUTED,       FG_SUBTLE),
    "primary": (PRIMARY_TINT_8, PRIMARY),
    "success": (SUCCESS_BG,     SUCCESS_DARK),
    "active":  (PRIMARY_TINT_8, PRIMARY),
    "queued":  (WARN_BG,        WARN_DARK),
    "error":   (ERROR_BG,       ERROR_DARK),
    "mono":    (BG_ACCENT,      FG_SUBTLE),
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
        self.setFixedSize(36, 24)
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
        p.setBrush(QColor(PRIMARY if self._checked else SURFACE_ALT))
        p.drawRoundedRect(0, 3, 36, 18, 9, 9)
        # thumb — 14×14, centered in 18px track (y=5), 3px side padding
        p.setBrush(QColor("white"))
        x = 19 if self._checked else 3
        p.drawEllipse(x, 5, 14, 14)

    def mousePressEvent(self, _event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()


# ── SlimProgressBar ───────────────────────────────────────────────────────────
class SlimProgressBar(QWidget):
    def __init__(self, color: str = PRIMARY, track: str = BORDER,
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
                 split_enabled: bool = True, compact: bool = False,
                 running: bool = False, parent=None):
        super().__init__(parent)
        self._active  = active_stage
        self._split   = split_enabled
        self._compact = compact
        self._running = running
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
                bg, fg, dot = PRIMARY_TINT_8, PRIMARY, PRIMARY
            else:
                bg, fg, dot = BG_SUBTLE, FG_MUTED, SURFACE_ALT

            pill = QWidget()
            pill.setToolTip(label)
            pl = QHBoxLayout(pill)
            pl.setContentsMargins(4 if self._compact else 8,
                                  2 if self._compact else 4,
                                  4 if self._compact else 8,
                                  2 if self._compact else 4)
            pl.setSpacing(4)

            if is_active and self._running:
                dot_w = Spinner(14 if not self._compact else 10, PRIMARY)
            elif is_active:
                # queued but not yet running — static dot same as active color
                dot_w = QLabel()
                dot_w.setFixedSize(6, 6)
                dot_w.setStyleSheet(f"background:{PRIMARY}; border-radius:3px;")
            else:
                dot_w = QLabel()
                dot_w.setFixedSize(6, 6)
                dot_w.setStyleSheet(f"background:{dot}; border-radius:3px;")
            pl.addWidget(dot_w)

            txt = QLabel(short if self._compact else label)
            txt.setTextFormat(Qt.PlainText)
            txt.setStyleSheet(
                f"color:{fg}; font-size:{'10' if self._compact else '11'}px; font-weight:500; "
                "background:transparent; border:none; text-decoration:none;"
            )
            pl.addWidget(txt)
            pill.setStyleSheet(f"background:{bg}; border-radius:8px;")
            lay.addWidget(pill)

            if i < len(stages) - 1:
                sep = QFrame()
                sep.setFixedSize(6 if self._compact else 10, 1)
                sep.setStyleSheet(f"background:{BORDER};")
                lay.addWidget(sep)

        lay.addStretch()

    def update_stage(self, active_stage: str, split_enabled: bool,
                     running: bool | None = None):
        self._active = active_stage
        self._split  = split_enabled
        if running is not None:
            self._running = running
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
            f"font-size:{TEXT_XS}px; font-weight:500; color:{FG_MUTED}; letter-spacing:0.04em;"
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
            hint_lbl.setStyleSheet(f"font-size:{TEXT_SM}px; color:{FG_MUTED};")
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


# ── status_dot ────────────────────────────────────────────────────────────────
def status_dot(color: str, size: int = 6) -> QLabel:
    dot = QLabel()
    dot.setFixedSize(size, size)
    dot.setStyleSheet(f"background:{color}; border-radius:{size // 2}px;")
    return dot


# ── IconButton ────────────────────────────────────────────────────────────────
def icon_button(icon_key: str, size: int = 28, icon_size: int = 14,
                color: str = FG_MUTED) -> QPushButton:
    btn = QPushButton()
    btn.setIcon(QIcon(icon_pixmap(icon_key, icon_size, color)))
    btn.setFixedSize(size, size)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton {{ background:{BG}; border:1px solid {BORDER}; border-radius:{RADIUS_MD}px; }}"
        f"QPushButton:hover {{ background:{BG_MUTED}; }}"
    )
    return btn


# ── field ─────────────────────────────────────────────────────────────────────
def field(label: str, widget: QWidget) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(SPACE_4)
    lbl = QLabel(label.upper())
    lbl.setStyleSheet(
        f"font-size:{TEXT_XS}px; font-weight:500; color:{FG_MUTED}; letter-spacing:.04em;"
    )
    lay.addWidget(lbl)
    lay.addWidget(widget)
    return w


# ── Checkbox ──────────────────────────────────────────────────────────────────
class Checkbox(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, color: str = PRIMARY, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._color = color
        self.setFixedSize(16, 16)
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
        if self._checked:
            p.setBrush(QColor(self._color))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(0, 0, 16, 16, RADIUS_SM, RADIUS_SM)
            p.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(3, 8, 6, 11)
            p.drawLine(6, 11, 13, 4)
        else:
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(BORDER), 1.5))
            p.drawRoundedRect(1, 1, 14, 14, RADIUS_SM - 1, RADIUS_SM - 1)

    def mousePressEvent(self, _event):
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        self.update()


# ── EmptyState ────────────────────────────────────────────────────────────────
class EmptyState(QWidget):
    def __init__(self, icon_key: str, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 30, 16, 30)
        lay.setSpacing(SPACE_8)
        lay.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        icon_w = QWidget()
        icon_w.setFixedSize(44, 44)
        icon_w.setStyleSheet(f"background:{BG_SUBTLE}; border-radius:8px;")
        i_lay = QHBoxLayout(icon_w)
        i_lay.setContentsMargins(0, 0, 0, 0)
        i_lay.addWidget(icon_label(icon_key, 20, FG_MUTED), alignment=Qt.AlignCenter)
        lay.addWidget(icon_w, alignment=Qt.AlignHCenter)

        t = QLabel(title)
        t.setStyleSheet(f"font-size:{TEXT_MD + 1}px; font-weight:500; color:{FG};")
        t.setAlignment(Qt.AlignHCenter)
        lay.addWidget(t)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"font-size:{TEXT_SM}px; color:{FG_MUTED};")
            sub.setAlignment(Qt.AlignHCenter)
            sub.setWordWrap(True)
            lay.addWidget(sub)


# ── BreathingDot ──────────────────────────────────────────────────────────────
class BreathingDot(QWidget):
    """Pulsing status dot with a soft halo ring.

    The dot and its halo breathe together — scale 1.0↔0.8, opacity 1.0↔0.55 —
    over a 1.4 s cosine cycle.  Pass *color* to reuse for other states
    (e.g. SUCCESS for a live/healthy indicator).
    """

    def __init__(self, color: str = PRIMARY, size: int = 14,
                 running: bool = True, parent=None):
        super().__init__(parent)
        self._color   = QColor(color)
        self._size    = size
        self._phase   = 0.0
        self._running = running
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if running:
            self._timer.start(20)   # 50 fps ≈ 70 steps/cycle at 1.4 s

    def set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._timer.start(20)
        else:
            self._timer.stop()
            self._phase = 0.0
            self.update()

    def _tick(self) -> None:
        self._phase = (self._phase + 1 / 70) % 1.0
        self.update()

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)

        cx = cy = self._size / 2

        if self._running:
            # cosine oscillation: 1.0 at phase=0, 0.0 at phase=0.5
            cos_t   = (math.cos(self._phase * 2 * math.pi) + 1) / 2
            scale   = 0.8 + cos_t * 0.2    # 0.8 → 1.0
            opacity = 0.55 + cos_t * 0.45  # 0.55 → 1.0
        else:
            scale, opacity = 1.0, 1.0

        # Both radii are derived from the same dot_r so they stay in lockstep.
        # dot_r  = base dot radius × scale
        # ring_r = dot_r + ring_width  (ring_width proportional to size)
        dot_r  = self._size * 0.22 * scale
        ring_r = dot_r + self._size * 0.21   # fixed 3 px ring at size=14

        halo = QColor(self._color)
        halo.setAlphaF(0.18 * opacity)
        p.setBrush(halo)
        p.drawEllipse(int(cx - ring_r), int(cy - ring_r),
                      int(ring_r * 2),  int(ring_r * 2))

        dot = QColor(self._color)
        dot.setAlphaF(opacity)
        p.setBrush(dot)
        p.drawEllipse(int(cx - dot_r), int(cy - dot_r),
                      int(dot_r * 2),  int(dot_r * 2))


# ── RoundedDialog ─────────────────────────────────────────────────────────────
class RoundedDialog(QDialog):
    """Base dialog with rounded corners, translucent background, and X button.

    Usage
    -----
    class MyDialog(RoundedDialog):
        def __init__(self, parent=None):
            super().__init__(title="My Title", width=480, parent=parent)
            # add widgets to self.body_layout (QVBoxLayout)

    The dialog renders:
        ┌─ card (white, border-radius 12px) ──────────────┐
        │  [ title ]                             [×]       │  ← header
        ├─────────────────────────────────────────────────┤
        │  self.body_layout                               │  ← body
        └─────────────────────────────────────────────────┘
    """

    def __init__(self, title: str = "", width: int = 480,
                 body_margins: tuple = (20, 16, 20, 20),
                 header_separator: bool = True,
                 header_height: int = 52,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(width)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._card = QWidget()
        self._card.setObjectName("roundedCard")
        self._card.setStyleSheet(
            f"#roundedCard {{ background:{BG}; border-radius:12px; border:none; }}"
        )
        outer.addWidget(self._card)

        self._root = QVBoxLayout(self._card)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # header
        hdr = QWidget(); hdr.setFixedHeight(header_height)
        hdr.setStyleSheet("background:transparent;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(20, 0, 16, 0)
        if title:
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet(f"font-size:15px; font-weight:700; color:{FG};")
            h_lay.addWidget(t_lbl)
        h_lay.addStretch()
        x_btn = QPushButton()
        x_btn.setIcon(QIcon(icon_pixmap("x", 14, FG_MUTED)))
        x_btn.setFixedSize(30, 30)
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; border-radius:6px; }}"
            f"QPushButton:hover {{ background:{BG_SUBTLE}; }}"
        )
        x_btn.clicked.connect(self.reject)
        h_lay.addWidget(x_btn)
        self._root.addWidget(hdr)

        # separator (optional)
        if header_separator:
            sep = QFrame(); sep.setFixedHeight(1)
            sep.setStyleSheet(f"background:{BORDER}; border:none;")
            self._root.addWidget(sep)

        # body
        body = QWidget(); body.setStyleSheet("background:transparent;")
        self.body_layout = QVBoxLayout(body)
        l, t, r, b = body_margins
        self.body_layout.setContentsMargins(l, t, r, b)
        self.body_layout.setSpacing(14)
        self._root.addWidget(body, 1)

    def add_footer(self, height: int = 60) -> QHBoxLayout:
        """Add a standard footer bar and return its QHBoxLayout."""
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        self._root.addWidget(sep)

        footer = QWidget(); footer.setFixedHeight(height)
        footer.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)
        self._root.addWidget(footer)
        return lay

    # ── drag to move ──────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
