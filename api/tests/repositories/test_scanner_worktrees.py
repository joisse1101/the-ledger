"""The scan attributes a Claude Code worktree session to the repo the worktree was split from."""

from app.repositories import settings_store
from app.repositories.db import paths, scanner

REPO = "/home/x/the-ledger"
WORKTREE = f"{REPO}/.claude/worktrees/add-wiki-docs"
TREES_WORKTREE = f"{REPO}/.trees/fix-nav"


def _scan_one(isolated_db, write_config, write_transcript, cwds: list[str], folder_cwd: str):
    write_config(isolated_db / "claude.json", {})
    lines = [
        {"type": "user", "timestamp": f"2024-01-01T10:0{i}:00Z", "cwd": cwd, "sessionId": "s1"}
        for i, cwd in enumerate(cwds)
    ]
    write_transcript(isolated_db / "projects" / paths.sanitize_project_path(folder_cwd) / "s1.jsonl", lines)
    (row,) = scanner.scan_transcripts({})
    return row


def test_worktree_session_belongs_to_the_repo(isolated_db, write_config, write_transcript):
    row = _scan_one(isolated_db, write_config, write_transcript, [WORKTREE], WORKTREE)
    assert row["worktree"] == "add-wiki-docs"
    assert row["project"] == "the-ledger"


def test_cd_into_a_subfolder_keeps_the_worktree(isolated_db, write_config, write_transcript):
    row = _scan_one(isolated_db, write_config, write_transcript, [WORKTREE, f"{WORKTREE}/api"], WORKTREE)
    assert row["worktree"] == "add-wiki-docs"
    assert row["project"] == "the-ledger"
    assert row["cwd"] == f"{WORKTREE}/api"


def test_cd_out_of_the_worktree_keeps_the_worktree(isolated_db, write_config, write_transcript):
    row = _scan_one(isolated_db, write_config, write_transcript, [WORKTREE, "/home/x/elsewhere"], WORKTREE)
    assert row["worktree"] == "add-wiki-docs"
    assert row["project"] == "the-ledger"


def test_ordinary_session_has_no_worktree(isolated_db, write_config, write_transcript):
    row = _scan_one(isolated_db, write_config, write_transcript, [REPO], REPO)
    assert row["worktree"] == ""
    assert row["project"] == "the-ledger"


def test_session_in_a_configured_folder_belongs_to_the_repo(isolated_db, write_config, write_transcript):
    settings_store.save_worktree_folders([".trees"])
    row = _scan_one(isolated_db, write_config, write_transcript, [TREES_WORKTREE], TREES_WORKTREE)
    assert row["worktree"] == "fix-nav"
    assert row["project"] == "the-ledger"


def test_session_in_an_unlisted_folder_is_its_own_project(isolated_db, write_config, write_transcript):
    row = _scan_one(isolated_db, write_config, write_transcript, [TREES_WORKTREE], TREES_WORKTREE)
    assert row["worktree"] == ""
    assert row["project"] == "fix-nav"
