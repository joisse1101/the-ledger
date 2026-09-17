"""Claude Code session transcript data.

Reads from the local SQLite snapshot (see claude_db.py) rather than parsing
~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl directly -
claude_db.refresh() does that parsing; this module just queries the result
and builds ClaudeTranscript dataclasses from it. Covers every session that
has ever run, including ones whose process has since exited - unlike the
live registry in claude_sessions.py.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import claude_db


@dataclass
class ClaudeTranscript:
    session_id: str
    path: Path
    cwd: str
    version: str
    git_branch: str
    started_at: Optional[datetime]
    updated_at: Optional[datetime]
    message_count: int
    cost: float
    project: str


def _row_to_transcript(row: sqlite3.Row) -> ClaudeTranscript:
    return ClaudeTranscript(
        session_id=row["session_id"],
        path=Path(row["path"]),
        cwd=row["cwd"],
        version=row["version"],
        git_branch=row["git_branch"],
        started_at=(
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        ),
        updated_at=(
            datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None
        ),
        message_count=row["message_count"],
        cost=row["cost"],
        project=row["project"],
    )


def load_transcripts() -> list[ClaudeTranscript]:
    """Every session transcript from the SQLite snapshot, newest-updated first."""
    return [_row_to_transcript(r) for r in claude_db.fetch_transcripts()]


def delete_project_transcripts(cwd: str) -> int:
    """Delete the on-disk transcript directory/directories for a given cwd,
    and their rows from the SQLite snapshot. Matches transcripts by their
    recorded `cwd` field rather than re-deriving Claude Code's
    directory-name sanitization, so it stays correct even if that scheme
    changes. Returns the number of directories removed.
    """
    dirs = {p.parent for p in claude_db.transcript_paths_for_cwd(cwd)}
    for d in dirs:
        shutil.rmtree(d, ignore_errors=True)
    claude_db.delete_transcript_rows_by_cwd(cwd)
    return len(dirs)


def delete_transcript(session_id: str) -> bool:
    """Delete a single session's transcript file by session_id, and its row
    from the SQLite snapshot. Returns True if it was found and deleted.
    """
    path = claude_db.transcript_path_for_session(session_id)
    if path is None:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    claude_db.delete_transcript_row(session_id)
    return True
