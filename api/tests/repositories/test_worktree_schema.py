"""The `worktree` column exists in a fresh ledger.db and is added to a pre-existing history.db."""

import sqlite3

from app.repositories.db import connection, paths, snapshot

LEGACY_HISTORY_TABLE = """
    CREATE TABLE transcripts (
        session_id TEXT PRIMARY KEY, path TEXT NOT NULL, cwd TEXT NOT NULL, version TEXT NOT NULL,
        git_branch TEXT NOT NULL, started_at TEXT, updated_at TEXT, message_count INTEGER NOT NULL,
        cost REAL NOT NULL, context INTEGER, project TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
        last_message TEXT NOT NULL DEFAULT '', first_prompt TEXT NOT NULL DEFAULT ''
    )
"""


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in conn.execute("PRAGMA table_info(transcripts)")}


def test_fresh_ledger_db_has_the_column(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    snapshot.refresh()
    with connection.connect() as conn:
        assert "worktree" in _columns(conn)


def test_existing_history_db_gains_the_column(isolated_db):
    legacy = sqlite3.connect(paths.history_db_path())
    legacy.execute(LEGACY_HISTORY_TABLE)
    legacy.commit()
    legacy.close()

    with connection.connect_history() as conn:
        assert "worktree" in _columns(conn)
