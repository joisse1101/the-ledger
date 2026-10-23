"""Where the snapshot, the history store and Claude Code's own data live on disk."""

from __future__ import annotations

from pathlib import Path

from app.core.worktrees import parse_worktree


def db_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".ledger" / "ledger.db"


def history_db_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".history" / "history.db"


def config_path() -> Path:
    return Path.home() / ".claude.json"


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def sanitize_project_path(path: str) -> str:
    """Project dir path -> its ~/.claude/projects/ folder name.

    - Every non-alphanumeric character becomes a dash, e.g.
      "C:/Users/x/Repos/the-log" -> "C--Users-x-Repos-the-log".
    """
    return "".join(ch if ch.isalnum() else "-" for ch in path)


def project_folder(transcript_path: Path, cwd: str, worktree: str) -> str:
    """The ~/.claude/projects/ folder name of the project a transcript belongs to.

    That is the transcript's own folder, except for a worktree session, which belongs to the repo
    the worktree was split from. A worktree transcript's folder is the repo's folder plus the
    sanitized worktree path, so the repo's folder is what is left after stripping it. `cwd` is only
    the fallback: it is the last directory seen, which a `cd` may have moved out of the worktree.
    """
    folder = transcript_path.parent.name
    if not worktree:
        return folder
    suffix = sanitize_project_path(f"/.claude/worktrees/{worktree}")
    if folder.endswith(suffix) and folder != suffix:
        return folder.removesuffix(suffix)
    parsed = parse_worktree(cwd)
    return sanitize_project_path(parsed.repo_root) if parsed else folder
