"""Recognising a Claude Code worktree from a working directory."""

import pytest

from app.core.worktrees import Worktree, normalize_folder, parse_worktree


def test_windows_path():
    assert parse_worktree(r"C:\Users\me\repos\the-ledger\.claude\worktrees\add-wiki-docs") == Worktree(
        "C:/Users/me/repos/the-ledger", "add-wiki-docs"
    )


def test_posix_path():
    assert parse_worktree("/home/me/the-ledger/.claude/worktrees/fix-login") == Worktree(
        "/home/me/the-ledger", "fix-login"
    )


def test_subfolder_of_a_worktree_is_that_worktree():
    result = parse_worktree(r"C:\repos\the-ledger\.claude\worktrees\add-wiki-docs\api\app")
    assert result == Worktree("C:/repos/the-ledger", "add-wiki-docs")


def test_name_with_plus():
    assert parse_worktree("/r/app/.claude/worktrees/feat+x").name == "feat+x"


def test_plain_repo_path_is_not_a_worktree():
    assert parse_worktree(r"C:\repos\the-ledger") is None


def test_empty_string_is_not_a_worktree():
    assert parse_worktree("") is None


def test_worktrees_folder_without_dot_claude_is_not_a_worktree():
    assert parse_worktree("/r/app/worktrees/feature") is None
    assert parse_worktree("/r/app/claude/worktrees/feature") is None


def test_worktrees_folder_itself_has_no_name():
    assert parse_worktree("/r/app/.claude/worktrees") is None
    assert parse_worktree("/r/app/.claude/worktrees/") is None


def test_configured_folder_is_a_worktree():
    assert parse_worktree(r"C:\repos\the-ledger\.trees\fix-nav", [".trees"]) == Worktree(
        "C:/repos/the-ledger", "fix-nav", ".trees"
    )


def test_session_deeper_in_a_configured_worktree():
    result = parse_worktree("C:/repos/the-ledger/.trees/fix-nav/web", [".trees"])
    assert result == Worktree("C:/repos/the-ledger", "fix-nav", ".trees")


def test_nested_configured_folder():
    assert parse_worktree("C:/repos/app/tools/wt/spike", ["tools/wt"]) == Worktree(
        "C:/repos/app", "spike", "tools/wt"
    )


def test_folder_not_in_the_list_is_not_a_worktree():
    assert parse_worktree("C:/repos/the-ledger/.trees/fix-nav") is None
    assert parse_worktree("C:/repos/the-ledger/.trees/fix-nav", ["wt"]) is None


def test_longer_folder_wins_over_its_prefix():
    result = parse_worktree("C:/repos/app/wt/inner/spike", ["wt", "wt/inner"])
    assert result == Worktree("C:/repos/app", "spike", "wt/inner")


def test_built_in_folder_still_applies_with_configured_folders():
    result = parse_worktree("/r/app/.claude/worktrees/feature", [".trees"])
    assert result == Worktree("/r/app", "feature", ".claude/worktrees")


def test_configured_folder_is_matched_literally():
    assert parse_worktree("/r/app/xtrees/feature", [".trees"]) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("tools\\wt\\", "tools/wt"), (".trees", ".trees"), ("  .trees/ ", ".trees")],
)
def test_normalize_folder(raw, expected):
    assert normalize_folder(raw) == expected


@pytest.mark.parametrize("raw", ["../shared", "C:/trees", "/trees", "\\trees", "a/./b", "a//b", "", "   ", "/"])
def test_normalize_folder_rejects(raw):
    with pytest.raises(ValueError):
        normalize_folder(raw)
