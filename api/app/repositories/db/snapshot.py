"""Rebuilding the SQLite snapshot from disk, and its start-up/shut-down lifecycle."""

from __future__ import annotations

import atexit
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.repositories.db import connection, history, paths, scanner


def refresh() -> datetime:
    """Rescan disk and replace the database's contents; returns the new refreshed-at timestamp."""
    project_rows = scanner.scan_projects()
    project_by_folder = {
        paths.sanitize_project_path(p["path"]): Path(p["path"]).name for p in project_rows
    }
    transcript_rows = scanner.scan_transcripts(project_by_folder)
    now = datetime.now()

    with connection.connect() as conn:
        conn.execute("DELETE FROM projects")
        conn.executemany(
            """
            INSERT INTO projects (
                path, trust_accepted, last_session_id, last_version, last_cost,
                last_start_time, last_duration_ms, lines_added, lines_removed,
                mcp_servers
            ) VALUES (
                :path, :trust_accepted, :last_session_id, :last_version, :last_cost,
                :last_start_time, :last_duration_ms, :lines_added, :lines_removed,
                :mcp_servers
            )
            """,
            [
                {
                    **p,
                    "last_start_time": (
                        p["last_start_time"].isoformat() if p["last_start_time"] else None
                    ),
                    "mcp_servers": json.dumps(p["mcp_servers"]),
                }
                for p in project_rows
            ],
        )

        conn.execute("DELETE FROM transcripts")
        conn.executemany(
            """
            INSERT INTO transcripts (
                session_id, path, cwd, version, git_branch, started_at,
                updated_at, message_count, cost, cost_source, unpriced_models, cost_state_flagged,
                model, used_openspec, context, project, worktree, title, last_message, first_prompt
            ) VALUES (
                :session_id, :path, :cwd, :version, :git_branch, :started_at,
                :updated_at, :message_count, :cost, :cost_source, :unpriced_models, :cost_state_flagged,
                :model, :used_openspec, :context, :project, :worktree, :title, :last_message, :first_prompt
            )
            """,
            [history.serialize_transcript_row(t) for t in transcript_rows],
        )

        conn.execute(
            """
            INSERT INTO meta (key, value) VALUES ('refreshed_at', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (now.isoformat(),),
        )

    return now


_started = False


def _remove_db_files(path: Path) -> None:
    """Delete the database and its WAL side files (best effort)."""
    for suffix in ("", "-wal", "-shm"):
        try:
            Path(f"{path}{suffix}").unlink(missing_ok=True)
        except OSError:
            pass


def startup() -> None:
    """Wipe any on-disk snapshot left over from a previous run and rebuild it fresh.

    - Database is a derived cache, never a source of truth
    - Registers a best-effort cleanup of the same files (including the WAL's
      `-wal`/`-shm` side files) on process exit
    """
    global _started
    if _started:
        return
    _started = True
    path = paths.db_path()
    _remove_db_files(path)
    history.correct_worktree_rows()
    refresh()
    atexit.register(_remove_db_files, path)


def refreshed_at() -> Optional[datetime]:
    """When the database was last refreshed, or None for a brand-new db."""
    with connection.connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = 'refreshed_at'").fetchone()
    return datetime.fromisoformat(row["value"]) if row else None
