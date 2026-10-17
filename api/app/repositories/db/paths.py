"""Where the snapshot, the history store and Claude Code's own data live on disk."""

from __future__ import annotations

from pathlib import Path


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
