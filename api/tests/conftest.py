import json
from pathlib import Path

import pytest

import claude_db


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point claude_db at a throwaway db/config/projects-dir under tmp_path
    so tests never touch the real ~/.claude.json or ~/.claude/projects/."""
    db_file = tmp_path / "ledger.db"
    config_file = tmp_path / "claude.json"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    monkeypatch.setattr(claude_db, "db_path", lambda: db_file)
    monkeypatch.setattr(claude_db, "config_path", lambda: config_file)
    monkeypatch.setattr(claude_db, "projects_dir", lambda: projects_dir)

    return tmp_path


@pytest.fixture
def write_config():
    def _write(path: Path, projects: dict) -> None:
        path.write_text(json.dumps({"projects": projects}), encoding="utf-8")

    return _write


@pytest.fixture
def write_transcript():
    def _write(path: Path, lines: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for entry in lines:
                f.write(json.dumps(entry) + "\n")

    return _write
