"""The user's dashboard settings, kept in a small JSON file under `api/.ledger/`."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.core.worktrees import normalize_folder

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[2] / ".ledger" / "settings.json"

# (path, mtime_ns, size) of the file last read, and the folders it held. Every transcript's project
# folder needs the list, so it is re-read only when the file changes.
_cache: Optional[tuple[tuple[str, int, int], tuple[str, ...]]] = None


def settings_path() -> Path:
    """The file from `LEDGER_SETTINGS_PATH`, else the default under `api/.ledger/`."""
    configured = os.environ.get("LEDGER_SETTINGS_PATH")
    return Path(configured) if configured else DEFAULT_PATH


def _read_folders(path: Path) -> tuple[str, ...]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8")).get("worktree_folders", [])
    except (OSError, ValueError, AttributeError) as err:
        logger.warning("settings_unreadable path=%s error=%s", path, err)
        return ()
    folders: list[str] = []
    for entry in raw if isinstance(raw, list) else []:
        try:
            folder = normalize_folder(entry) if isinstance(entry, str) else None
        except ValueError:
            folder = None
        if folder is None:
            logger.warning("settings_folder_skipped path=%s entry=%r", path, entry)
        elif folder not in folders:
            folders.append(folder)
    return tuple(folders)


def load_worktree_folders() -> tuple[str, ...]:
    """The user's worktree folders (never the built-in one); empty when the file is missing or invalid."""
    global _cache
    path = settings_path()
    try:
        stat = path.stat()
    except FileNotFoundError:
        return ()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    if _cache is None or _cache[0] != key:
        _cache = (key, _read_folders(path))
    return _cache[1]


def save_worktree_folders(folders: list[str]) -> None:
    """Replace the stored worktree folders. Written to a temp file first, so a crash never leaves half a file."""
    global _cache
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.tmp")
    temp.write_text(json.dumps({"worktree_folders": list(folders)}, indent=2), encoding="utf-8")
    os.replace(temp, path)
    _cache = None
