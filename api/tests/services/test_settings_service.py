"""Saving the worktree folders takes effect at once in both stores, and invalid lists are refused."""

import pytest

from app.repositories import claude_transcripts, settings_store
from app.repositories.db import history, paths, snapshot
from app.services import settings_service
from app.services.errors import InvalidInput

WORKTREE = "/home/x/the-ledger/.trees/fix-nav"


def _pruned_row(session_id: str, cwd: str) -> dict:
    return {
        "session_id": session_id, "path": f"/gone/{session_id}.jsonl", "cwd": cwd, "version": "1",
        "git_branch": "main", "started_at": None, "updated_at": None, "message_count": 1,
        "cost": 0.0, "cost_source": "estimated", "unpriced_models": [], "cost_state_flagged": False,
        "context": None, "project": "fix-nav", "title": "", "last_message": "", "first_prompt": "",
    }


@pytest.fixture
def trees_sessions(isolated_db, write_config, write_transcript):
    """One `.trees` session on disk and one only in history, both filed as a `fix-nav` project."""
    write_config(isolated_db / "claude.json", {})
    write_transcript(
        isolated_db / "projects" / paths.sanitize_project_path(WORKTREE) / "live.jsonl",
        [{"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": WORKTREE, "sessionId": "live"}],
    )
    history.upsert_history_transcripts([_pruned_row("pruned", WORKTREE)])
    snapshot.refresh()


def _attribution():
    return {t.session_id: (t.project, t.worktree) for t in claude_transcripts.load_transcripts()}


def test_adding_then_removing_a_folder_moves_sessions_and_back(trees_sessions):
    before = _attribution()
    assert before == {"live": ("fix-nav", ""), "pruned": ("fix-nav", "")}

    settings_service.save_worktree_folders([".trees"])
    assert _attribution() == {"live": ("the-ledger", "fix-nav"), "pruned": ("the-ledger", "fix-nav")}

    settings_service.save_worktree_folders([])
    assert _attribution() == before


def test_the_list_starts_with_the_built_in_folder(isolated_settings):
    assert settings_service.get_worktree_folders() == [settings_service.WorktreeFolder(".claude/worktrees", True)]


def test_saved_folders_are_normalised_and_kept_in_order(isolated_db):
    folders = settings_service.save_worktree_folders(["tools\\wt\\", ".trees"])
    assert [(f.path, f.built_in) for f in folders] == [
        (".claude/worktrees", True), ("tools/wt", False), (".trees", False)
    ]
    assert settings_store.load_worktree_folders() == ("tools/wt", ".trees")


@pytest.mark.parametrize(
    ("folders", "reason"),
    [
        (["../shared"], "inside the repo"),
        (["C:/trees"], "inside the repo"),
        ([".trees", ".trees/"], "already listed"),
        ([".claude/worktrees"], "already listed"),
        ([""], "Enter a folder"),
    ],
)
def test_an_invalid_list_is_refused_and_nothing_changes(isolated_db, folders, reason):
    settings_store.save_worktree_folders([".trees"])
    with pytest.raises(InvalidInput, match=reason):
        settings_service.save_worktree_folders(folders)
    assert settings_store.load_worktree_folders() == (".trees",)
