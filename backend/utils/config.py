"""Simple JSON config stored at ~/.anees/config.json."""
from __future__ import annotations
import json
from pathlib import Path

_DIR  = Path.home() / ".anees"
_FILE = _DIR / "config.json"

_DEFAULTS: dict = {
    "output_root": str(Path.home() / "Downloads" / "Anees"),
}


def _load() -> dict:
    try:
        return json.loads(_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get(key: str, default=None):
    return _load().get(key, _DEFAULTS.get(key, default))


def set(key: str, value) -> None:  # noqa: A001
    _DIR.mkdir(parents=True, exist_ok=True)
    data = _load()
    data[key] = value
    _FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_output_root() -> str:
    return get("output_root")


def set_output_root(path: str) -> None:
    set("output_root", path)


def check_disk_space(
    estimated_mb: float,
    output_root: str,
    margin: float = 1.20,
) -> tuple[bool, float, float]:
    """Check whether the output folder has enough free space.

    Applies a 20 % safety margin on top of the raw estimate to account
    for temp files, metadata, and CBR overhead variation.

    Returns (has_space, required_mb, free_mb).
    """
    import shutil
    from pathlib import Path
    try:
        Path(output_root).mkdir(parents=True, exist_ok=True)
        free_mb = shutil.disk_usage(output_root).free / 1024 / 1024
    except Exception:
        return True, 0.0, 0.0   # can't check — let it proceed
    required_mb = estimated_mb * margin
    return free_mb >= required_mb, required_mb, free_mb
