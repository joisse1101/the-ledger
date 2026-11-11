"""The user's dashboard settings, kept in a small JSON file under `api/.ledger/`."""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.widget_settings import (
    DEFAULT_AFK_MINUTES,
    DEFAULT_BREAK_MINUTES,
    DEFAULT_MAX_PROJECTS,
    validate_afk_minutes,
    validate_break_minutes,
    validate_max_projects,
)
from app.core.worktrees import normalize_folder
from app.repositories.json_file import write_json_atomic

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[2] / ".ledger" / "settings.json"

WORKTREE_FOLDERS_KEY = "worktree_folders"
MAX_PROJECTS_KEY = "widget_max_projects"
AFK_MINUTES_KEY = "widget_afk_minutes"
BREAK_MINUTES_KEY = "widget_break_minutes"


@dataclass(frozen=True)
class _Loaded:
    """What a read of the file produced: the raw keys (to write back unchanged) and each setting."""

    raw: dict
    worktree_folders: tuple[str, ...]
    max_projects: int
    afk_minutes: int
    break_minutes: int


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


def _afk_minutes_from(raw: dict, path: Path) -> int:
    if AFK_MINUTES_KEY not in raw:
        return DEFAULT_AFK_MINUTES
    try:
        return validate_afk_minutes(raw[AFK_MINUTES_KEY])
    except ValueError:
        logger.warning("settings_afk_minutes_skipped path=%s value=%r", path, raw[AFK_MINUTES_KEY])
        return DEFAULT_AFK_MINUTES


def _break_minutes_from(raw: dict, path: Path) -> int:
    if BREAK_MINUTES_KEY not in raw:
        return DEFAULT_BREAK_MINUTES
    try:
        return validate_break_minutes(raw[BREAK_MINUTES_KEY])
    except ValueError:
        logger.warning("settings_break_minutes_skipped path=%s value=%r", path, raw[BREAK_MINUTES_KEY])
        return DEFAULT_BREAK_MINUTES


def _load() -> _Loaded:
    global _cache
    path = settings_path()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return _Loaded(
            raw={},
            worktree_folders=(),
            max_projects=DEFAULT_MAX_PROJECTS,
            afk_minutes=DEFAULT_AFK_MINUTES,
            break_minutes=DEFAULT_BREAK_MINUTES,
        )
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if _cache is None or _cache[0] != key:
        raw = _read_raw(path)
        _cache = (
            key,
            _Loaded(
                raw,
                _folders_from(raw, path),
                _max_projects_from(raw, path),
                _afk_minutes_from(raw, path),
                _break_minutes_from(raw, path),
            ),
        )
    return _cache[1]


def load_worktree_folders() -> tuple[str, ...]:
    """The user's worktree folders (never the built-in one); empty when the file is missing or invalid."""
    return _load().worktree_folders


def load_max_projects() -> int:
    """How many projects the widget lists; the default when never set or not a valid number."""
    return _load().max_projects


def load_afk_minutes() -> int:
    """How long the widget's AFK switch stays on, in minutes; the default when never set or not valid."""
    return _load().afk_minutes


def load_break_minutes() -> int:
    """Minutes of work before the widget's break window opens; the default when never set or not valid."""
    return _load().break_minutes


def _save_key(key: str, value: object) -> None:
    """Set one key and write the whole file back, keeping every other key as it is.

    Written atomically, so a crash never leaves half a file.
    """
    global _cache
    path = settings_path()
    with _write_lock:
        raw = _read_raw(path) if path.exists() else {}
        raw[key] = value
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, raw)
        _cache = None


def save_worktree_folders(folders: list[str]) -> None:
    """Replace the stored worktree folders."""
    _save_key(WORKTREE_FOLDERS_KEY, list(folders))


def save_max_projects(max_projects: int) -> None:
    """Replace the stored number of projects the widget lists."""
    _save_key(MAX_PROJECTS_KEY, max_projects)


def save_afk_minutes(afk_minutes: int) -> None:
    """Replace the stored minutes the widget's AFK switch stays on."""
    _save_key(AFK_MINUTES_KEY, afk_minutes)


def save_break_minutes(break_minutes: int) -> None:
    """Replace the stored minutes of work before the widget's break window opens."""
    _save_key(BREAK_MINUTES_KEY, break_minutes)
