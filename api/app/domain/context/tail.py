"""Reading a live session's context size and latest activity from the end of its transcript."""

from __future__ import annotations

import json
import os
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Optional

from app.repositories.db import paths
from app.repositories.db import scanner
from app.domain.context.models import LiveContext, Turn
from app.domain.context.parsing import extract_turns


SPARKLINE_TURNS = 24
_TAIL_WINDOW = 256 * 1024


def _read_tail_turns(path: Path, limit: int = SPARKLINE_TURNS) -> list[Turn]:
    """The last `limit` real turns, reading backwards from EOF in a window that doubles until enough are found."""
    window = _TAIL_WINDOW
    with path.open("rb") as f:
        size = f.seek(0, os.SEEK_END)
        while True:
            start = max(0, size - window)
            f.seek(start)
            lines = f.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]  # the window probably began mid-record
            turns = extract_turns(line.decode("utf-8", errors="replace") for line in lines)
            if len(turns) >= limit or start == 0:
                return turns[-limit:]
            window *= 2


# session id -> transcript found by glob rather than by its sanitized cwd
_located: dict[str, Path] = {}


def transcript_path(session_id: str, cwd: str) -> Optional[Path]:
    root = paths.projects_dir()
    direct = root / paths.sanitize_project_path(cwd) / f"{session_id}.jsonl"
    if direct.is_file():
        return direct

    remembered = _located.get(session_id)
    if remembered is not None and remembered.is_file():
        return remembered

    found = next(root.glob(f"*/{session_id}.jsonl"), None)
    if found is not None:
        _located[session_id] = found
    return found


def stat_key(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


# path -> (stat key at last read, result)
_live_cache: dict[Path, tuple[tuple[int, int], Optional[LiveContext]]] = {}


def live_context(session_id: str, cwd: str) -> Optional[LiveContext]:
    """The session's current context size, growth and recent history, or None when unavailable. Never raises."""
    try:
        path = transcript_path(session_id, cwd)
        if path is None:
            return None
        key = stat_key(path)
        cached = _live_cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]

        sizes = [turn.context for turn in _read_tail_turns(path)]
        result = (
            LiveContext(size=sizes[-1], growth=sizes[-1] - sizes[-2] if len(sizes) > 1 else None, history=sizes)
            if sizes
            else None
        )
        _live_cache[path] = (key, result)
        return result
    except (OSError, ValueError):
        return None


def _read_tail_latest_timestamp(path: Path) -> Optional[datetime]:
    """The newest `user` line's timestamp near EOF, in a window that doubles until one is found.

    Only `user` lines count (a tool result, or something the person typed): those are what appear
    once a dialog has been answered. `assistant` lines and bookkeeping lines (`attachment`,
    `system`, ...) can be written while a dialog is still open, e.g. a later tool call of the same
    parallel batch still streaming in, and must not read as "the prompt was answered".
    """
    window = _TAIL_WINDOW
    with path.open("rb") as f:
        size = f.seek(0, os.SEEK_END)
        while True:
            start = max(0, size - window)
            f.seek(start)
            lines = f.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]  # the window probably began mid-record
            latest: Optional[datetime] = None
            for line in lines:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "user":
                    continue
                stamp = scanner.parse_iso_timestamp(entry.get("timestamp"))
                if stamp is None:
                    continue
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                if latest is None or stamp > latest:
                    latest = stamp
            if latest is not None or start == 0:
                return latest
            window *= 2


# path -> (stat key at last read, latest timestamp)
_activity_cache: dict[Path, tuple[tuple[int, int], Optional[datetime]]] = {}


def latest_activity(session_id: str, cwd: str) -> Optional[datetime]:
    """When the session's transcript last got a `user` line (by the line's own timestamp), or None. Never raises.

    Lets the pending-prompt store tell that a session moved on (a tool result was written) after a
    prompt was registered - the line's timestamp, not the file's mtime, so a line flushed late but
    stamped before the prompt can't be mistaken for progress. Only `user` lines count; see
    `_read_tail_latest_timestamp`.
    """
    try:
        path = transcript_path(session_id, cwd)
        if path is None:
            return None
        key = stat_key(path)
        cached = _activity_cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]

        latest = _read_tail_latest_timestamp(path)
        _activity_cache[path] = (key, latest)
        return latest
    except (OSError, ValueError):
        return None
