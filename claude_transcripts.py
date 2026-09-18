"""Claude Code session transcript data, read from the SQLite snapshot claude_db.py maintains.

Covers every session that has ever run (unlike claude_sessions.py's live-only registry).
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
    return [_row_to_transcript(row) for row in claude_db.fetch_transcripts()]


def delete_project_transcripts(cwd: str) -> int:
    """Delete a project's on-disk transcript dir(s) and their SQLite rows; returns dirs removed."""
    # Matched by the recorded `cwd` field rather than re-deriving Claude
    # Code's directory-name sanitization, so this stays correct even if
    # that naming scheme changes.
    transcript_dirs = {path.parent for path in claude_db.transcript_paths_for_cwd(cwd)}
    for directory in transcript_dirs:
        shutil.rmtree(directory, ignore_errors=True)
    claude_db.delete_transcript_rows_by_cwd(cwd)
    return len(transcript_dirs)


def delete_transcript(session_id: str) -> bool:
    """Delete one session's transcript file and its SQLite row; True if it was found."""
    path = claude_db.transcript_path_for_session(session_id)
    if path is None:
        return False
    try:
        path.unlink()
    except OSError:
        return False
    claude_db.delete_transcript_row(session_id)
    return True
