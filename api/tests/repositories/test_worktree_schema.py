"""The `worktree` column exists in a fresh ledger.db and is added to a pre-existing history.db."""

import sqlite3

from app.repositories import settings_store
from app.repositories.db import connection, history, paths, snapshot

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


WORKTREE_CWD = "/home/x/the-ledger/.claude/worktrees/add-wiki-docs"


def _legacy_row(session_id: str, cwd: str, project: str) -> dict:
    return {
        "session_id": session_id, "path": f"/gone/{session_id}.jsonl", "cwd": cwd, "version": "1",
        "git_branch": "main", "started_at": None, "updated_at": None, "message_count": 1,
        "cost": 0.0, "cost_source": "estimated", "unpriced_models": [], "cost_state_flagged": False,
        "context": None, "project": project, "title": "", "last_message": "", "first_prompt": "",
    }


def test_correction_pass_fixes_legacy_rows_and_is_idempotent(isolated_db):
    history.upsert_history_transcripts(
        [
            _legacy_row("wt", WORKTREE_CWD + "/api", "api"),
            _legacy_row("plain", "/home/x/other", "other"),
        ]
    )

    def snapshot_of_rows():
        return {r["session_id"]: (r["worktree"], r["project"]) for r in history.fetch_history_transcripts()}

    history.correct_worktree_rows()
    first = snapshot_of_rows()
    assert first == {"wt": ("add-wiki-docs", "the-ledger"), "plain": ("", "other")}

    history.correct_worktree_rows()
    assert snapshot_of_rows() == first


TREES_CWD = "C:/repos/the-ledger/.trees/fix-nav"


def _worktrees_and_projects():
    return {r["session_id"]: (r["worktree"], r["project"]) for r in history.fetch_history_transcripts()}


def test_pruned_row_gains_and_loses_a_configured_worktree(isolated_db):
    history.upsert_history_transcripts([_legacy_row("trees", TREES_CWD, "fix-nav")])

    settings_store.save_worktree_folders([".trees"])
    history.correct_worktree_rows()
    assert _worktrees_and_projects() == {"trees": ("fix-nav", "the-ledger")}

    settings_store.save_worktree_folders([])
    history.correct_worktree_rows()
    assert _worktrees_and_projects() == {"trees": ("", "fix-nav")}


def test_built_in_rows_never_revert(isolated_db):
    filed = paths.sanitize_project_path(WORKTREE_CWD)
    moved_out = {**_legacy_row("moved", "/home/x/elsewhere", "the-ledger"), "path": f"/p/{filed}/moved.jsonl"}
    history.upsert_history_transcripts([_legacy_row("wt", WORKTREE_CWD, "add-wiki-docs"), moved_out])
    with connection.connect_history() as conn:
        conn.execute("UPDATE transcripts SET worktree = 'add-wiki-docs' WHERE session_id = 'moved'")

    for folders in ([".trees"], []):
        settings_store.save_worktree_folders(folders)
        history.correct_worktree_rows()
        assert _worktrees_and_projects() == {
            "wt": ("add-wiki-docs", "the-ledger"),
            "moved": ("add-wiki-docs", "the-ledger"),
        }


def test_reconcile_with_an_unchanged_list_changes_nothing(isolated_db):
    history.upsert_history_transcripts(
        [_legacy_row("trees", TREES_CWD, "fix-nav"), _legacy_row("wt", WORKTREE_CWD, "add-wiki-docs")]
    )
    settings_store.save_worktree_folders([".trees"])
    history.correct_worktree_rows()
    first = _worktrees_and_projects()
    history.correct_worktree_rows()
    assert _worktrees_and_projects() == first
