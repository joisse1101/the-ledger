import json
from pathlib import Path

import pytest

from app import deps
from app.repositories.db import paths


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point the db paths at a throwaway db/config/projects-dir under tmp_path
    so tests never touch the real ~/.claude.json or ~/.claude/projects/."""
    db_file = tmp_path / "ledger.db"
    history_db_file = tmp_path / "history.db"
    config_file = tmp_path / "claude.json"
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    monkeypatch.setattr(paths, "db_path", lambda: db_file)
    monkeypatch.setattr(paths, "history_db_path", lambda: history_db_file)
    monkeypatch.setattr(paths, "config_path", lambda: config_file)
    monkeypatch.setattr(paths, "projects_dir", lambda: projects_dir)

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


class _InertRemote:
    """Stands in for deps.remote so no test starts, stops or probes real Docker."""

    def status(self):
        return {"state": "off", "step": None, "reason": None}

    def is_ready(self):
        return False

    def start(self):
        pass

    def stop(self):
        pass

    def stop_leftovers(self):
        pass


@pytest.fixture(autouse=True)
def no_real_remote_mode(monkeypatch):
    """Remote mode drives real Docker, so every test gets an inert one unless it installs its own.
    cli.main(--reload) also exports the ports for the reload subprocess: set-then-unset makes
    monkeypatch restore the environment afterwards."""
    monkeypatch.setattr(deps, "remote", _InertRemote())
    for name in ("LEDGER_PORT", "LEDGER_FRONTEND_PORT"):
        monkeypatch.setenv(name, "0")
        monkeypatch.delenv(name)
