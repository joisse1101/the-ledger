"""Recognising a Claude Code worktree from a working directory."""

from app.core.worktrees import Worktree, parse_worktree


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
