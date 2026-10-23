"""The durable history store (`history.db`): transcript rows that outlive the snapshot."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.core.worktrees import parse_worktree
from app.repositories.db import connection


def serialize_transcript_row(row: dict[str, Any]) -> dict[str, Any]:
    """A `scan_transcripts()`-shaped row (Path/datetime fields) -> one ready for SQLite binding."""
    return {
        **row,
        "path": str(row["path"]),
        "started_at": row["started_at"].isoformat() if row["started_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "unpriced_models": json.dumps(row["unpriced_models"]),
        "model": row.get("model", ""),
        "used_openspec": int(row.get("used_openspec", False)),
        "worktree": row.get("worktree", ""),
    }


_TRANSCRIPT_UPSERT_SQL = """
    INSERT INTO transcripts (
        session_id, path, cwd, version, git_branch, started_at,
        updated_at, message_count, cost, cost_source, unpriced_models, cost_state_flagged, model,
        used_openspec, context, project, worktree, title, last_message, first_prompt
    ) VALUES (
        :session_id, :path, :cwd, :version, :git_branch, :started_at,
        :updated_at, :message_count, :cost, :cost_source, :unpriced_models, :cost_state_flagged,
        :model, :used_openspec, :context, :project, :worktree, :title, :last_message, :first_prompt
    )
    ON CONFLICT(session_id) DO UPDATE SET
        path = excluded.path,
        cwd = excluded.cwd,
        version = excluded.version,
        git_branch = excluded.git_branch,
        started_at = excluded.started_at,
        updated_at = excluded.updated_at,
        message_count = excluded.message_count,
        cost = excluded.cost,
        cost_source = excluded.cost_source,
        unpriced_models = excluded.unpriced_models,
        cost_state_flagged = excluded.cost_state_flagged,
        model = excluded.model,
        used_openspec = excluded.used_openspec,
        context = excluded.context,
        project = excluded.project,
        worktree = excluded.worktree,
        title = excluded.title,
        last_message = excluded.last_message,
        first_prompt = excluded.first_prompt
"""


def upsert_history_transcripts(rows: list[dict[str, Any]]) -> None:
    """Insert or update `history.db` transcript rows, keyed by `session_id`.

    `rows` is `scan_transcripts()`-shaped (Path/datetime fields, one dict per transcript).
    A row whose `session_id` already exists is overwritten in place rather than duplicated,
    so re-running a backup against a still-growing session never creates a second row for it.
    """
    if not rows:
        return
    with connection.connect_history() as conn:
        conn.executemany(_TRANSCRIPT_UPSERT_SQL, [serialize_transcript_row(r) for r in rows])


def correct_worktree_rows() -> None:
    """Give rows recorded before worktrees were tracked their worktree and parent project.

    Works from the stored `cwd`, so rows whose transcript was pruned from disk are corrected too.
    Idempotent: a corrected row has a worktree and is not selected again.
    """
    with connection.connect_history() as conn:
        rows = conn.execute("SELECT session_id, cwd FROM transcripts WHERE worktree = ''").fetchall()
        for row in rows:
            worktree = parse_worktree(row["cwd"])
            if worktree is not None:
                conn.execute(
                    "UPDATE transcripts SET worktree = ?, project = ? WHERE session_id = ?",
                    (worktree.name, Path(worktree.repo_root).name, row["session_id"]),
                )


def fetch_history_transcripts() -> list[sqlite3.Row]:
    """Every transcript row ever backed up to `history.db`, including ones since pruned from disk."""
    with connection.connect_history() as conn:
        return conn.execute("SELECT * FROM transcripts").fetchall()
