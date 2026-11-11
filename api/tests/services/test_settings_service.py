"""Saving the worktree folders takes effect at once in both stores, and invalid lists are refused."""

import pytest

from app.repositories import claude_transcripts, settings_store
from app.repositories.db import history, paths, snapshot
from app.services import settings_service
from app.services.errors import InvalidInput, OperationFailed

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

    settings_service.save_settings([".trees"], None)
    assert _attribution() == {"live": ("the-ledger", "fix-nav"), "pruned": ("the-ledger", "fix-nav")}

    settings_service.save_settings([], None)
    assert _attribution() == before


def test_the_list_starts_with_the_built_in_folder(isolated_settings):
    assert settings_service.get_worktree_folders() == [settings_service.WorktreeFolder(".claude/worktrees", True)]


def test_saved_folders_are_normalised_and_kept_in_order(isolated_db):
    settings_service.save_settings(["tools\\wt\\", ".trees"], None)
    folders = settings_service.get_worktree_folders()
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
        settings_service.save_settings(folders, None)
    assert settings_store.load_worktree_folders() == (".trees",)


def test_the_widget_number_defaults_to_five(isolated_settings):
    assert settings_service.get_max_projects() == 5


def test_saving_the_widget_number_leaves_the_folders_and_the_stores_alone(isolated_db, monkeypatch):
    settings_service.save_settings([".trees"], None)
    reconciled = []
    monkeypatch.setattr(history, "correct_worktree_rows", lambda: reconciled.append("history"))
    monkeypatch.setattr(snapshot, "refresh", lambda: reconciled.append("snapshot"))

    settings_service.save_settings(None, 3)

    assert settings_service.get_max_projects() == 3
    assert settings_store.load_worktree_folders() == (".trees",)
    assert reconciled == []


def test_saving_over_an_unreadable_settings_file_fails_and_names_the_file(isolated_settings):
    isolated_settings.write_text("{not json", encoding="utf-8")
    with pytest.raises(OperationFailed, match="settings.json"):
        settings_service.save_settings(None, 3)
    assert isolated_settings.read_text(encoding="utf-8") == "{not json"


def test_saving_folders_leaves_the_widget_number(isolated_db):
    settings_service.save_settings(None, 3)
    settings_service.save_settings([".trees"], None)
    assert settings_service.get_max_projects() == 3


@pytest.mark.parametrize("value", [0, 11, -1, 2.5, True, "3", [3]])
def test_an_invalid_widget_number_is_refused_and_nothing_changes(isolated_db, value):
    settings_service.save_settings(None, 4)
    with pytest.raises(InvalidInput):
        settings_service.save_settings(None, value)
    assert settings_service.get_max_projects() == 4


def test_the_afk_minutes_default_to_thirty(isolated_settings):
    assert settings_service.get_afk_minutes() == 30


def test_saving_the_afk_minutes_changes_only_them(isolated_db, monkeypatch):
    settings_service.save_settings([".trees"], 3)
    reconciled = []
    monkeypatch.setattr(history, "correct_worktree_rows", lambda: reconciled.append("history"))
    monkeypatch.setattr(snapshot, "refresh", lambda: reconciled.append("snapshot"))

    settings_service.save_settings(None, None, 10)

    assert settings_service.get_afk_minutes() == 10
    assert settings_service.get_max_projects() == 3
    assert settings_store.load_worktree_folders() == (".trees",)
    assert reconciled == []


def test_saving_folders_and_max_projects_leaves_the_afk_minutes(isolated_db):
    settings_service.save_settings(None, None, 10)
    settings_service.save_settings([".trees"], 3)
    assert settings_service.get_afk_minutes() == 10


@pytest.mark.parametrize("value", [0, 241, -1, 7.5, True, "30", [30]])
def test_invalid_afk_minutes_are_refused_and_nothing_changes(isolated_db, value):
    settings_service.save_settings(None, None, 20)
    with pytest.raises(InvalidInput, match="whole number"):
        settings_service.save_settings(None, None, value)
    assert settings_service.get_afk_minutes() == 20


def test_bad_afk_minutes_stop_valid_folders_and_max_projects_from_being_saved(isolated_db):
    with pytest.raises(InvalidInput):
        settings_service.save_settings([".trees"], 3, 999)
    assert settings_store.load_worktree_folders() == ()
    assert settings_service.get_max_projects() == 5


def test_a_bad_number_stops_valid_folders_from_being_saved(isolated_db):
    with pytest.raises(InvalidInput):
        settings_service.save_settings([".trees"], 99)
    assert settings_store.load_worktree_folders() == ()


def test_the_break_minutes_default_to_sixty(isolated_settings):
    assert settings_service.get_break_minutes() == 60


def test_saving_the_break_minutes_changes_only_them(isolated_db, monkeypatch):
    settings_service.save_settings([".trees"], 3, 10)
    reconciled = []
    monkeypatch.setattr(history, "correct_worktree_rows", lambda: reconciled.append("history"))
    monkeypatch.setattr(snapshot, "refresh", lambda: reconciled.append("snapshot"))

    settings_service.save_settings(None, None, None, 45)

    assert settings_service.get_break_minutes() == 45
    assert settings_service.get_afk_minutes() == 10
    assert settings_service.get_max_projects() == 3
    assert settings_store.load_worktree_folders() == (".trees",)
    assert reconciled == []


def test_saving_the_other_settings_leaves_the_break_minutes(isolated_db):
    settings_service.save_settings(None, None, None, 45)
    settings_service.save_settings([".trees"], 3, 10)
    assert settings_service.get_break_minutes() == 45


@pytest.mark.parametrize("value", [0, 241, -1, 7.5, True, "60", [60]])
def test_invalid_break_minutes_are_refused_and_nothing_changes(isolated_db, value):
    settings_service.save_settings(None, None, None, 20)
    with pytest.raises(InvalidInput, match="whole number"):
        settings_service.save_settings(None, None, None, value)
    assert settings_service.get_break_minutes() == 20


def test_bad_break_minutes_stop_the_other_settings_from_being_saved(isolated_db):
    with pytest.raises(InvalidInput):
        settings_service.save_settings([".trees"], 3, 10, 999)
    assert settings_store.load_worktree_folders() == ()
    assert settings_service.get_afk_minutes() == 30
