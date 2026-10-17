"""Imports point downward only: routers -> services -> repositories/domain -> core.

Scans every module under app/ for what it imports, so a layer can't quietly start depending on one
above it (a repository importing a router, a service importing FastAPI).
"""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# The app packages each layer (or single-file module) may import from, besides itself.
ALLOWED = {
    "core": set(),
    "infra": {"core"},
    "repositories": {"core"},
    "domain": {"core", "repositories"},
    "schemas": {"core", "domain", "infra", "repositories"},
    "services": {"core", "deps", "domain", "infra", "refresh", "repositories"},
    "routers": {"core", "schemas", "services"},
    "deps": {"core", "domain", "infra"},
    "refresh": {"repositories"},
}
# Layers that hold no web-framework code.
FRAMEWORK_FREE = {"repositories", "domain", "infra", "services"}
FRAMEWORKS = {"fastapi", "starlette"}


def _imports(path: Path) -> set[str]:
    """Dotted names a module imports; `from app import x` counts as `app.x`."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module == "app":
                names.update(f"app.{alias.name}" for alias in node.names)
            else:
                names.add(node.module)
    return names


def _layer(path: Path) -> str:
    parts = path.relative_to(APP_DIR).parts
    return parts[0].removesuffix(".py")


def _violations() -> list[str]:
    found = []
    for path in sorted(APP_DIR.rglob("*.py")):
        layer = _layer(path)
        if layer not in ALLOWED:
            continue  # entry points (main, cli, __main__) may wire anything together
        for name in _imports(path):
            top = name.split(".")
            target = top[1] if top[0] == "app" and len(top) > 1 else None
            where = path.relative_to(APP_DIR).as_posix()
            if target is not None and target != layer and target not in ALLOWED[layer]:
                found.append(f"{where} ({layer}) imports app.{target}")
            if layer in FRAMEWORK_FREE and top[0] in FRAMEWORKS:
                found.append(f"{where} ({layer}) imports {top[0]}")
    return found


def test_layers_only_import_downward():
    assert _violations() == []


def test_every_layer_is_covered():
    """A new top-level package has to be given a place in ALLOWED (or be an entry point)."""
    entry_points = {"main", "cli", "__main__", "__init__"}
    names = {_layer(p) for p in APP_DIR.rglob("*.py")}
    assert names - set(ALLOWED) - entry_points == set()
