"""Reads and deletes against the SQLite snapshot."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable, Optional

from app.repositories.db import connection, history, paths


def fetch_projects() -> list[sqlite3.Row]:
    """Every project row, newest-started first (NULLs last)."""
    with connection.connect() as conn:
        return conn.execute(
            "SELECT * FROM projects ORDER BY last_start_time IS NULL, last_start_time DESC"
        ).fetchall()


def fetch_transcripts() -> list[sqlite3.Row]:
    """Every transcript row, live `ledger.db` rows merged with `history.db`'s durable rows by
    `session_id` (the live row wins whenever a session exists in both - it's the fresher scan),
    newest-updated first (NULLs last)."""
    with connection.connect() as conn:
        live_rows = conn.execute("SELECT * FROM transcripts").fetchall()
    history_rows = history.fetch_history_transcripts()

    merged: dict[str, sqlite3.Row] = {row["session_id"]: row for row in history_rows}
    merged.update({row["session_id"]: row for row in live_rows})

    # Empty string sorts before any ISO timestamp, so `reverse=True` puts NULLs
    # (mapped to "") last while still ordering real timestamps newest-first.
    return sorted(merged.values(), key=lambda row: row["updated_at"] or "", reverse=True)


def git_branches(session_ids: list[str]) -> dict[str, str]:
    """`git_branch` per session id from `ledger.db`; ids it has no row for are left out."""
    if not session_ids:
        return {}
    marks = ",".join("?" * len(session_ids))
    with connection.connect() as conn:
        rows = conn.execute(
            f"SELECT session_id, git_branch FROM transcripts WHERE session_id IN ({marks})", session_ids
        ).fetchall()
    return {row["session_id"]: row["git_branch"] for row in rows}


def delete_project_row(project_path: str) -> None:
    with connection.connect() as conn:
        conn.execute("DELETE FROM projects WHERE path = ?", (project_path,))


def _is_member(row: sqlite3.Row, folder: str) -> bool:
    return paths.project_folder(Path(row["path"]), row["cwd"], row["worktree"]) == folder


def _member_rows(folder: str) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    """`ledger.db`'s transcript rows split into (members of the project, everything else)."""
    with connection.connect() as conn:
        rows = conn.execute("SELECT session_id, path, cwd, worktree FROM transcripts").fetchall()
    members = [row for row in rows if _is_member(row, folder)]
    return members, [row for row in rows if not _is_member(row, folder)]


def transcript_paths_for_project(project_path: str) -> list[Path]:
    """Transcript file paths belonging to `project_path`: those filed under its own
    `~/.claude/projects/` folder, and those of sessions that ran in its Claude Code worktrees.

    Matched by on-disk folder name (see `paths.project_folder`) rather than each transcript's own
    recorded `cwd` - a session can `cd` partway through and leave `cwd` pointing below the
    project root, but the folder a transcript is filed under never changes.
    """
    members, _ = _member_rows(paths.sanitize_project_path(project_path))
    return list(dict.fromkeys(Path(row["path"]) for row in members))


def transcript_dirs_for_project(project_path: str) -> set[Path]:
    """Folders holding the project's transcripts, leaving out any that also hold another project's."""
    members, others = _member_rows(paths.sanitize_project_path(project_path))
    shared = {Path(row["path"]).parent for row in others}
    return {Path(row["path"]).parent for row in members} - shared


def _delete_transcript_rows_by_project_in(
    connect: Callable[[], Any], folder: str
) -> None:
    with connect() as conn:
        rows = conn.execute("SELECT session_id, path, cwd, worktree FROM transcripts").fetchall()
        session_ids = [row["session_id"] for row in rows if _is_member(row, folder)]
        if session_ids:
            conn.executemany(
                "DELETE FROM transcripts WHERE session_id = ?",
                [(sid,) for sid in session_ids],
            )


def delete_transcript_rows_by_project(project_path: str) -> None:
    """Remove a project's transcript rows from both `ledger.db` and `history.db`.

    Matched by the same on-disk folder name `transcript_paths_for_project` uses, since a
    `history.db` row (a session already pruned from disk) carries the same `path` shape.
    """
    folder = paths.sanitize_project_path(project_path)
    _delete_transcript_rows_by_project_in(connection.connect, folder)
    _delete_transcript_rows_by_project_in(connection.connect_history, folder)


def transcript_path_for_session(session_id: str) -> Optional[Path]:
    """A session's transcript path from `ledger.db`, falling back to `history.db` when the
    session is no longer live (e.g. already pruned from disk) - so callers checking whether a
    session is known at all (the delete route's 404 check) recognize a history-only session too.
    """
    with connection.connect() as conn:
        row = conn.execute(
            "SELECT path FROM transcripts WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is not None:
        return Path(row["path"])
    with connection.connect_history() as conn:
        row = conn.execute(
            "SELECT path FROM transcripts WHERE session_id = ?", (session_id,)
        ).fetchone()
    return Path(row["path"]) if row else None


def delete_transcript_row(session_id: str) -> None:
    """Remove one session's row from whichever of `ledger.db`/`history.db` has it."""
    with connection.connect() as conn:
        conn.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))
    with connection.connect_history() as conn:
        conn.execute("DELETE FROM transcripts WHERE session_id = ?", (session_id,))
