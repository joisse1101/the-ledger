"""Parser for Claude Code's global config (~/.claude.json), which tracks
every project directory Claude Code has been trusted/run in."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def config_path() -> Path:
    return Path.home() / ".claude.json"


@dataclass
class ClaudeProject:
    path: str
    trust_accepted: bool
    last_session_id: Optional[str]
    last_version: str
    last_cost: Optional[float]
    last_start_time: Optional[datetime]
    last_duration_ms: Optional[int]
    lines_added: Optional[int]
    lines_removed: Optional[int]
    mcp_servers: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def name(self) -> str:
        return Path(self.path).name


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000)


def _parse_project(path: str, data: dict[str, Any]) -> ClaudeProject:
    return ClaudeProject(
        path=path,
        trust_accepted=bool(data.get("hasTrustDialogAccepted", False)),
        last_session_id=data.get("lastSessionId"),
        last_version=data.get("lastVersionBase", ""),
        last_cost=data.get("lastCost"),
        last_start_time=_parse_timestamp(data.get("lastStartTime")),
        last_duration_ms=data.get("lastDuration"),
        lines_added=data.get("lastLinesAdded"),
        lines_removed=data.get("lastLinesRemoved"),
        mcp_servers=sorted(data.get("mcpServers", {}).keys()),
        raw=data,
    )


# mtime at last parse, parsed projects
_cache: tuple[float, list[ClaudeProject]] | None = None


def load_projects(path: Optional[Path] = None) -> list[ClaudeProject]:
    """Read every project entry from ~/.claude.json, newest-started first.

    Cached by the config file's mtime — unchanged files are served from
    cache instead of being re-read/re-parsed.
    """
    global _cache

    path = path or config_path()
    if not path.is_file():
        _cache = None
        return []

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return []

    if _cache is not None and _cache[0] == mtime:
        return _cache[1]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    projects_data = data.get("projects", {})
    projects = [
        _parse_project(project_path, project_data)
        for project_path, project_data in projects_data.items()
    ]
    projects.sort(
        key=lambda p: p.last_start_time or datetime.min,
        reverse=True,
    )

    _cache = (mtime, projects)
    return projects


def delete_project(project_path: str, path: Optional[Path] = None) -> bool:
    """Remove a project entry from ~/.claude.json.

    Returns True if the entry was found and removed, False otherwise.
    Invalidates the module-level cache so the next load_projects() call
    re-reads the file.
    """
    global _cache

    path = path or config_path()
    if not path.is_file():
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    projects_data = data.get("projects", {})
    if project_path not in projects_data:
        return False

    del projects_data[project_path]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _cache = None
    return True
