import json

import claude_db
import claude_projects


def test_load_projects_maps_fields(isolated_db, write_config):
    tmp_path = isolated_db
    write_config(
        tmp_path / "claude.json",
        {
            "/home/x/the-ledger": {
                "hasTrustDialogAccepted": True,
                "lastSessionId": "sess-1",
                "lastVersionBase": "1.0.0",
                "lastCost": 1.5,
                "lastStartTime": 1_700_000_000_000,
                "lastDuration": 60000,
                "lastLinesAdded": 10,
                "lastLinesRemoved": 2,
                "mcpServers": {"b-server": {}, "a-server": {}},
            }
        },
    )
    claude_db.refresh()

    projects = claude_projects.load_projects()
    assert len(projects) == 1
    p = projects[0]
    assert p.path == "/home/x/the-ledger"
    assert p.name == "the-ledger"
    assert p.trust_accepted is True
    assert p.last_session_id == "sess-1"
    assert p.last_version == "1.0.0"
    assert p.last_cost == 1.5
    assert p.last_duration_ms == 60000
    assert p.lines_added == 10
    assert p.lines_removed == 2
    assert p.mcp_servers == ["a-server", "b-server"]


def test_load_projects_empty(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {})
    claude_db.refresh()
    assert claude_projects.load_projects() == []


def test_delete_project_removes_entry_and_row(isolated_db, write_config):
    tmp_path = isolated_db
    config_file = tmp_path / "claude.json"
    write_config(config_file, {"/a": {}, "/b": {}})
    claude_db.refresh()

    removed = claude_projects.delete_project("/a")
    assert removed is True

    remaining_on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert list(remaining_on_disk["projects"].keys()) == ["/b"]

    remaining_in_db = claude_projects.load_projects()
    assert [p.path for p in remaining_in_db] == ["/b"]


def test_delete_project_returns_false_when_not_found(isolated_db, write_config):
    write_config(isolated_db / "claude.json", {"/a": {}})
    claude_db.refresh()
    assert claude_projects.delete_project("/does-not-exist") is False


def test_delete_project_returns_false_when_no_config_file(isolated_db):
    assert claude_projects.delete_project("/a") is False
