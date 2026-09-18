"""Parser for Claude Code's live session registry (~/.claude/sessions/<pid>.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from claude_transcripts import load_transcripts


def sessions_dir() -> Path:
    return Path.home() / ".claude" / "sessions"


@dataclass
class ClaudeSession:
    pid: int
    session_id: str
    cwd: str
    name: str
    status: str
    kind: str
    entrypoint: str
    version: str
    started_at: Optional[datetime]
    updated_at: Optional[datetime]
    status_updated_at: Optional[datetime]
    raw: dict[str, Any] = field(repr=False)
    # Set in load_sessions() from the transcripts table, not just this field.
    project: str = ""


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000)


def _parse_session_file(path: Path) -> Optional[ClaudeSession]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if "pid" not in data or "sessionId" not in data:
        return None

    return ClaudeSession(
        pid=data["pid"],
        session_id=data["sessionId"],
        cwd=data.get("cwd", ""),
        name=data.get("name", ""),
        status=data.get("status", "unknown"),
        kind=data.get("kind", "unknown"),
        entrypoint=data.get("entrypoint", "unknown"),
        version=data.get("version", ""),
        started_at=_parse_timestamp(data.get("startedAt")),
        updated_at=_parse_timestamp(data.get("updatedAt")),
        status_updated_at=_parse_timestamp(data.get("statusUpdatedAt")),
        raw=data,
        project=Path(data.get("cwd", "")).name,
    )


# path -> (mtime at last parse, parsed session)
_cache: dict[Path, tuple[float, ClaudeSession]] = {}


def load_sessions(directory: Optional[Path] = None) -> list[ClaudeSession]:
    """Every live session, newest-updated first (unchanged files are served from a cache)."""
    directory = directory or sessions_dir()
    if not directory.is_dir():
        _cache.clear()
        return []

    seen_paths: set[Path] = set()
    sessions: list[ClaudeSession] = []

    for path in directory.glob("*.json"):
        seen_paths.add(path)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue

        cached = _cache.get(path)
        if cached is not None and cached[0] == mtime:
            sessions.append(cached[1])
            continue

        session = _parse_session_file(path)
        if session is None:
            _cache.pop(path, None)
            continue

        _cache[path] = (mtime, session)
        sessions.append(session)

    for stale_path in _cache.keys() - seen_paths:
        del _cache[stale_path]

    project_by_session_id = {
        transcript.session_id: transcript.project for transcript in load_transcripts()
    }
    for session in sessions:
        project = project_by_session_id.get(session.session_id)
        if project:
            session.project = project

    sessions.sort(
        key=lambda session: session.updated_at or datetime.min,
        reverse=True,
    )
    return sessions
