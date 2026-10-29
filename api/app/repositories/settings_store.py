"""The user's dashboard settings, kept in a small JSON file under `api/.ledger/`."""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.widget_settings import DEFAULT_MAX_PROJECTS, validate_max_projects
from app.core.worktrees import normalize_folder

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[2] / ".ledger" / "settings.json"

WORKTREE_FOLDERS_KEY = "worktree_folders"
MAX_PROJECTS_KEY = "widget_max_projects"


@dataclass(frozen=True)
class _Loaded:
    """What a read of the file produced: the raw keys (to write back unchanged) and each setting."""

    raw: dict
    worktree_folders: tuple[str, ...]
    max_projects: int


# (path, mtime_ns, size) of the file last read, and what it held. Every transcript's project
# folder needs the folder list, so the file is re-read only when it changes.
_cache: Optional[tuple[tuple[str, int, int], _Loaded]] = None
# A save is a read-modify-write of the whole file; two at once (folders and widget) must not lose one.
_write_lock = threading.Lock()


def settings_path() -> Path:
    """The file from `LEDGER_SETTINGS_PATH`, else the default under `api/.ledger/`."""
    configured = os.environ.get("LEDGER_SETTINGS_PATH")
    return Path(configured) if configured else DEFAULT_PATH


def _read_raw(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        logger.warning("settings_unreadable path=%s error=%s", path, err)
        return {}
    if not isinstance(raw, dict):
        logger.warning("settings_unreadable path=%s error=not an object", path)
        return {}
    return raw


def _folders_from(raw: dict, path: Path) -> tuple[str, ...]:
    entries = raw.get(WORKTREE_FOLDERS_KEY, [])
    folders: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        try:
            folder = normalize_folder(entry) if isinstance(entry, str) else None
        except ValueError:
            folder = None
        if folder is None:
            logger.warning("settings_folder_skipped path=%s entry=%r", path, entry)
        elif folder not in folders:
            folders.append(folder)
    return tuple(folders)


def _max_projects_from(raw: dict, path: Path) -> int:
    if MAX_PROJECTS_KEY not in raw:
        return DEFAULT_MAX_PROJECTS
    try:
        return validate_max_projects(raw[MAX_PROJECTS_KEY])
    except ValueError:
        logger.warning("settings_max_projects_skipped path=%s value=%r", path, raw[MAX_PROJECTS_KEY])
        return DEFAULT_MAX_PROJECTS


def _load() -> _Loaded:
    global _cache
    path = settings_path()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return _Loaded(raw={}, worktree_folders=(), max_projects=DEFAULT_MAX_PROJECTS)
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if _cache is None or _cache[0] != key:
        raw = _read_raw(path)
        _cache = (key, _Loaded(raw, _folders_from(raw, path), _max_projects_from(raw, path)))
    return _cache[1]


def load_worktree_folders() -> tuple[str, ...]:
    """The user's worktree folders (never the built-in one); empty when the file is missing or invalid."""
    return _load().worktree_folders


def load_max_projects() -> int:
    """How many projects the widget lists; the default when never set or not a valid number."""
    return _load().max_projects


def _save_key(key: str, value: object) -> None:
    """Set one key and write the whole file back, keeping every other key as it is.

    Written to a temp file first, so a crash never leaves half a file.
    """
    global _cache
    path = settings_path()
    with _write_lock:
        raw = _read_raw(path) if path.exists() else {}
        raw[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f"{path.name}.tmp")
        temp.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        os.replace(temp, path)
        _cache = None


def save_worktree_folders(folders: list[str]) -> None:
    """Replace the stored worktree folders."""
    _save_key(WORKTREE_FOLDERS_KEY, list(folders))


def save_max_projects(max_projects: int) -> None:
    """Replace the stored number of projects the widget lists."""
    _save_key(MAX_PROJECTS_KEY, max_projects)
