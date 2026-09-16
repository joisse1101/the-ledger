"""Parser for Claude Code's live session registry (~/.claude/sessions/<pid>.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


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

    @property
    def project(self) -> str:
        return Path(self.cwd).name


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
    )


def load_sessions(directory: Optional[Path] = None) -> list[ClaudeSession]:
    """Read and parse every session file, newest-updated first."""
    directory = directory or sessions_dir()
    if not directory.is_dir():
        return []

    sessions = [
        session
        for path in directory.glob("*.json")
        if (session := _parse_session_file(path)) is not None
    ]
    sessions.sort(
        key=lambda s: s.updated_at or datetime.min,
        reverse=True,
    )
    return sessions
