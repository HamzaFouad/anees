from __future__ import annotations
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer

from ui.theme import (
    FG, FG_MUTED, BG, BG_MUTED, BORDER,
    RADIUS_LG, RADIUS_MD, TEXT_XS, SPACE_4,
    make_icon_svg,
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
    return (
        f"#{object_name} {{ "
        f"border:1px solid {border}; border-radius:{radius}px; background:{background}; "
        "}"
    )


def make_transparent_row(widget: QWidget) -> None:
    widget.setAttribute(Qt.WA_NoSystemBackground, True)
    widget.setAttribute(Qt.WA_OpaquePaintEvent, False)
    widget.setAutoFillBackground(False)
    widget.setStyleSheet("background:transparent; border:none;")


def hsep(color: str = BORDER, parent=None) -> QFrame:
    sep = QFrame(parent)
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background:{color}; border:none;")
    return sep


def status_dot(color: str, size: int = 6) -> QLabel:
    dot = QLabel()
    dot.setFixedSize(size, size)
    dot.setStyleSheet(f"background:{color}; border-radius:{size // 2}px;")
    return dot


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
