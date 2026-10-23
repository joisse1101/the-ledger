"""Claude Code session transcript data, read from the SQLite snapshot `app/repositories/db/` maintains.

Covers every session that has ever run (unlike claude_sessions.py's live-only registry).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.repositories.db import paths, queries


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
    cost_source: str
    project: str
    title: str
    last_message: str
    first_prompt: str
    # Context size at the last real main-thread response (see app/domain/context/); None if there wasn't one.
    context: Optional[int] = None
    # Model ids this app's own pricing table didn't recognize during the per-message fallback scan -
    # empty whenever every turn's model was priced (including every `exact` session).
    unpriced_models: list[str] = field(default_factory=list)
    # True only when a `cost-state` line was found and it flagged `hasUnknownModelCost` itself -
    # distinguishes that case from `estimated` meaning "no cost-state line at all yet" (always False
    # on an `exact` session, where a clean cost-state line was found instead).
    cost_state_flagged: bool = False
    # The model with the most main-thread responses in the session; "" if it had none.
    model: str = ""
    # True if the session ran an OpenSpec (`/opsx:*` or `openspec-*`) command or skill.
    used_openspec: bool = False
    # Name of the Claude Code worktree the session ran in; "" when it did not run in one.
    worktree: str = ""

    @property
    def project_folder(self) -> str:
        """The ~/.claude/projects/ folder name of the project this session belongs to."""
        return paths.project_folder(self.path, self.cwd, self.worktree)


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
        cost_source=row["cost_source"],
        project=row["project"],
        title=row["title"],
        last_message=row["last_message"],
        first_prompt=row["first_prompt"],
        context=row["context"],
        unpriced_models=json.loads(row["unpriced_models"]) if row["unpriced_models"] else [],
        cost_state_flagged=bool(row["cost_state_flagged"]),
        model=row["model"],
        used_openspec=bool(row["used_openspec"]),
        worktree=row["worktree"],
    )


def load_transcripts() -> list[ClaudeTranscript]:
    """Every session transcript from the SQLite snapshot, newest-updated first."""
    return [_row_to_transcript(row) for row in queries.fetch_transcripts()]


def delete_project_transcripts(project_path: str) -> int:
    """Delete a project's on-disk transcript dir(s) and their SQLite rows; returns dirs removed."""
    # Matched by the on-disk folder a transcript is filed under (see
    # queries.transcript_paths_for_project), not by each transcript's own recorded `cwd` -
    # that can point below the project root if a session `cd`'d partway through. The project's
    # worktree sessions are filed under folders of their own and go with it.
    transcript_dirs = queries.transcript_dirs_for_project(project_path)
    for directory in transcript_dirs:
        shutil.rmtree(directory, ignore_errors=True)
    queries.delete_transcript_rows_by_project(project_path)
    return len(transcript_dirs)


def delete_transcript(session_id: str) -> bool:
    """Delete one session's transcript file and its SQLite row(s); True if it was found.

    A history-only session (already pruned from disk, known only from `history.db`) has no
    file left to remove - `unlink()`'s `FileNotFoundError` is treated as "already gone" rather
    than a failure, and the row purge still runs against whichever store has it.
    """
    path = queries.transcript_path_for_session(session_id)
    if path is None:
        return False
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return False
    queries.delete_transcript_row(session_id)
    return True
