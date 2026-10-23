"""SQLite connections and schemas for the snapshot (`ledger.db`) and the history store (`history.db`)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Generator

from app.repositories.db import paths


_BUSY_TIMEOUT_MS = 10_000


@contextmanager
def _connect_to(
    path: Path, ensure: Callable[[sqlite3.Connection], None]
) -> Generator[sqlite3.Connection, None, None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=_BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    try:
        # WAL lets the API's readers keep reading while a writer commits its
        # own table replacement; the timeout makes the rare remaining collision wait.
        conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA journal_mode = WAL")
        ensure(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def connect() -> Generator[sqlite3.Connection, None, None]:
    with _connect_to(paths.db_path(), ensure_schema) as conn:
        yield conn


@contextmanager
def connect_history() -> Generator[sqlite3.Connection, None, None]:
    with _connect_to(paths.history_db_path(), ensure_history_schema) as conn:
        yield conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS projects (
            path TEXT PRIMARY KEY,
            trust_accepted INTEGER NOT NULL,
            last_session_id TEXT,
            last_version TEXT NOT NULL,
            last_cost REAL,
            last_start_time TEXT,
            last_duration_ms INTEGER,
            lines_added INTEGER,
            lines_removed INTEGER,
            mcp_servers TEXT NOT NULL
        );
        """
    )
    ensure_history_schema(conn)


def ensure_history_schema(conn: sqlite3.Connection) -> None:
    """`transcripts` table shape shared by ledger.db (disposable) and history.db (durable)."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS transcripts (
            session_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            cwd TEXT NOT NULL,
            version TEXT NOT NULL,
            git_branch TEXT NOT NULL,
            started_at TEXT,
            updated_at TEXT,
            message_count INTEGER NOT NULL,
            cost REAL NOT NULL,
            cost_source TEXT NOT NULL DEFAULT 'estimated',
            unpriced_models TEXT NOT NULL DEFAULT '[]',
            cost_state_flagged INTEGER NOT NULL DEFAULT 0,
            model TEXT NOT NULL DEFAULT '',
            used_openspec INTEGER NOT NULL DEFAULT 0,
            context INTEGER,
            project TEXT NOT NULL,
            worktree TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            last_message TEXT NOT NULL DEFAULT '',
            first_prompt TEXT NOT NULL DEFAULT ''
        );
        """
    )
    # history.db is never recreated, so a pre-existing file's table predates these
    # columns - add them in place. ledger.db's CREATE TABLE above already includes
    # them (that table is dropped and rebuilt every start), so this is a no-op
    # there beyond the harmless "duplicate column" error being swallowed.
    for ddl in (
        "ALTER TABLE transcripts ADD COLUMN cost_source TEXT NOT NULL DEFAULT 'estimated'",
        "ALTER TABLE transcripts ADD COLUMN unpriced_models TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE transcripts ADD COLUMN cost_state_flagged INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE transcripts ADD COLUMN model TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE transcripts ADD COLUMN used_openspec INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE transcripts ADD COLUMN worktree TEXT NOT NULL DEFAULT ''",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass
