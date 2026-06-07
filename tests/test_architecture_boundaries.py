"""Architecture guardrail tests for import boundaries."""
from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _py_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
    )


def _import_targets(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                targets.add(node.module)
    return targets


def _violations(files: list[Path], forbidden_prefixes: tuple[str, ...]) -> list[str]:
    bad: list[str] = []
    for path in files:
        imports = _import_targets(path)
        for target in imports:
            if any(target == prefix or target.startswith(f"{prefix}.") for prefix in forbidden_prefixes):
                bad.append(f"{path.relative_to(REPO_ROOT)} imports {target}")
    return sorted(set(bad))


def test_ui_does_not_import_backend_services_or_commands_or_utils_config():
    ui_files = _py_files(REPO_ROOT / "ui")
    bad = _violations(
        ui_files,
        (
            "backend.services",
            "backend.commands",
            "backend.utils.config",
        ),
    )
    assert not bad, "UI boundary violation(s):\n" + "\n".join(bad)


def test_backend_services_do_not_import_ui():
    service_files = _py_files(REPO_ROOT / "backend" / "services")
    bad = _violations(service_files, ("ui",))
    assert not bad, "backend/services must not import ui:\n" + "\n".join(bad)


def test_backend_commands_do_not_import_ui():
    command_files = _py_files(REPO_ROOT / "backend" / "commands")
    bad = _violations(command_files, ("ui",))
    assert not bad, "backend/commands must not import ui:\n" + "\n".join(bad)
