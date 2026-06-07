"""Platform-aware resource and user-path helpers."""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Return bundle root in frozen mode, repo root otherwise."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def bundled_resource_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def images_dir() -> Path:
    if is_frozen():
        return bundled_resource_path("images")
    return app_root() / "ui" / "images"


def app_icon_path() -> Path:
    base = images_dir()
    if sys.platform == "darwin":
        icns = base / "anees.icns"
        if icns.exists():
            return icns
    return base / "anees.ico"


def user_config_dir() -> Path:
    return Path.home() / ".anees"


def user_data_dir() -> Path:
    return Path.home() / ".anees"


def logs_dir() -> Path:
    return user_data_dir() / "logs"
