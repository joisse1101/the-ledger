"""Claude Code project data.

Reads from the local SQLite snapshot (see claude_db.py) rather than parsing
~/.claude.json directly - claude_db.refresh() does that parsing; this module
just queries the result and builds ClaudeProject dataclasses from it.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import claude_db


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
    mcp_servers: list[str]

    @property
    def name(self) -> str:
        return Path(self.path).name


def _row_to_project(row: sqlite3.Row) -> ClaudeProject:
    return ClaudeProject(
        path=row["path"],
        trust_accepted=bool(row["trust_accepted"]),
        last_session_id=row["last_session_id"],
        last_version=row["last_version"],
        last_cost=row["last_cost"],
        last_start_time=(
            datetime.fromisoformat(row["last_start_time"])
            if row["last_start_time"]
            else None
        ),
        last_duration_ms=row["last_duration_ms"],
        lines_added=row["lines_added"],
        lines_removed=row["lines_removed"],
        mcp_servers=json.loads(row["mcp_servers"]),
    )


def load_projects() -> list[ClaudeProject]:
    """Every project entry from the SQLite snapshot, newest-started first."""
    return [_row_to_project(r) for r in claude_db.fetch_projects()]


def delete_project(project_path: str) -> bool:
    """Remove a project entry from ~/.claude.json and its row from the
    SQLite snapshot. Returns True if the entry was found and removed."""
    path = claude_db.config_path()
    if not path.is_file():
        return False

    data = json.loads(path.read_text(encoding="utf-8"))
    projects_data = data.get("projects", {})
    if project_path not in projects_data:
        return False

    del projects_data[project_path]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    claude_db.delete_project_row(project_path)
    return True
