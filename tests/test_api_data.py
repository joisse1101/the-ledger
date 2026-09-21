"""The data endpoints (/api/live, /api/transcripts, ...) over throwaway ~/.claude fixtures."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import claude_db
import server
from claude_context import LiveContext
from claude_sessions import ClaudeSession
from live_snapshot import LiveSnapshot


def _client():
    """A client the security middleware treats as the browser on this machine."""
    return TestClient(
        server.app,
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
        headers={"X-Requested-With": "ledger"},
    )


def _live_session(session_id="live-1", cwd="/h/alpha", pid=7):
    return ClaudeSession(
        pid=pid, session_id=session_id, cwd=cwd, name="n", status="busy", kind="interactive", entrypoint="cli",
        version="2", started_at=datetime(2024, 1, 1, 9), updated_at=datetime(2024, 1, 1, 10),
        status_updated_at=None, raw={}, project="alpha",
    )


def _use_live(monkeypatch, sessions=(), context=lambda session_id, cwd: None):
    monkeypatch.setattr(
        server, "live", LiveSnapshot(load_sessions=lambda: list(sessions), live_context=context)
    )


def _add_session(root, write_transcript, session_id, cwd, *, branch="main", version="1.0", text="hello",
                 ts="2024-01-01T10:00:00Z"):
    folder = claude_db.sanitize_project_path(cwd)
    write_transcript(
        root / "projects" / folder / f"{session_id}.jsonl",
        [
            {"type": "user", "timestamp": ts, "cwd": cwd, "version": version, "gitBranch": branch,
             "sessionId": session_id, "message": {"content": text}},
        ],
    )


@pytest.fixture
def seeded(isolated_db, write_config, write_transcript):
    write_config(isolated_db / "claude.json", {})
    _add_session(isolated_db, write_transcript, "aaa-1", "/h/alpha", branch="main", text="fix the a.b thing",
                 ts="2024-01-01T10:00:00Z")
    _add_session(isolated_db, write_transcript, "bbb-2", "/h/alpha", branch="dev", text="axb is different",
                 ts="2024-01-02T10:00:00Z")
    _add_session(isolated_db, write_transcript, "ccc-3", "/h/beta", branch="main", version="2.0", text="third",
                 ts="2024-01-03T10:00:00Z")
    claude_db.refresh()
    return isolated_db


@pytest.fixture
def api(seeded, monkeypatch):
    _use_live(monkeypatch)
    return _client()


def _ids(response):
    return [item["session_id"] for item in response.json()["items"]]


# ---------------------------------------------------------------- /api/live


def test_live_lists_sessions_with_context(isolated_db, monkeypatch):
    _use_live(
        monkeypatch,
        [_live_session()],
        context=lambda session_id, cwd: LiveContext(394_000, 2_100, [390_000, 394_000]),
    )
    body = _client().get("/api/live").json()
    assert [s["session_id"] for s in body["sessions"]] == ["live-1"]
    assert body["sessions"][0]["context"]["label"].startswith("394k ▲ +2.1k ")
    assert "cwd" not in body["sessions"][0]


def test_live_with_nothing_running_is_an_empty_list(isolated_db, monkeypatch):
    _use_live(monkeypatch)
    assert _client().get("/api/live").json() == {"sessions": []}


# ---------------------------------------------------------------- /api/transcripts


def test_transcripts_default_order_is_newest_updated_first_with_iso_dates(api):
    response = api.get("/api/transcripts")
    assert response.status_code == 200
    assert _ids(response) == ["ccc-3", "bbb-2", "aaa-1"]
    assert response.json()["items"][0]["updated_at"].startswith("2024-01-03T10:00:00")
    assert response.json()["total"] == 3


def test_transcripts_filters_combine(api):
    assert _ids(api.get("/api/transcripts", params={"project": "alpha", "branch": "main"})) == ["aaa-1"]
    both = api.get("/api/transcripts", params={"project": ["alpha", "beta"], "branch": "main"})
    assert _ids(both) == ["ccc-3", "aaa-1"]
    assert _ids(api.get("/api/transcripts", params={"version": "2.0"})) == ["ccc-3"]


def test_transcripts_search_is_literal(api):
    assert _ids(api.get("/api/transcripts", params={"q": "a.b"})) == ["aaa-1"]


def test_transcripts_total_reflects_matches_not_the_page(api):
    body = api.get("/api/transcripts", params={"project": "alpha", "limit": 1}).json()
    assert len(body["items"]) == 1
    assert body["total"] == 2
    second = api.get("/api/transcripts", params={"project": "alpha", "limit": 1, "offset": 1}).json()
    assert second["items"][0]["session_id"] != body["items"][0]["session_id"]


def test_transcripts_options_cover_the_unfiltered_list(api):
    body = api.get("/api/transcripts", params={"project": "beta"}).json()
    assert body["options"] == {
        "projects": ["alpha", "beta"],
        "versions": ["1.0", "2.0"],
        "branches": ["dev", "main"],
    }


def test_transcripts_sort_and_direction(api):
    ascending = api.get("/api/transcripts", params={"sort": "session_id", "dir": "asc"})
    descending = api.get("/api/transcripts", params={"sort": "session_id", "dir": "desc"})
    assert _ids(ascending) == ["aaa-1", "bbb-2", "ccc-3"]
    assert _ids(descending) == ["ccc-3", "bbb-2", "aaa-1"]


@pytest.mark.parametrize(
    "params",
    [{"sort": "path"}, {"sort": "nope"}, {"dir": "sideways"}, {"limit": 0}, {"limit": 100000}, {"offset": -1}],
)
def test_transcripts_bad_parameters_are_422_not_a_crash(api, params):
    assert api.get("/api/transcripts", params=params).status_code == 422


def test_transcripts_flags_live_sessions(seeded, monkeypatch):
    _use_live(monkeypatch, [_live_session("bbb-2")])
    items = {i["session_id"]: i for i in _client().get("/api/transcripts").json()["items"]}
    assert items["bbb-2"]["live"] is True
    assert items["aaa-1"]["live"] is False


# ---------------------------------------------------------------- /api/overview


def test_overview_all_time_has_summary_and_chart_arrays(api):
    body = api.get("/api/overview").json()
    assert body["empty"] is False
    assert body["summary"]["sessions"] == 3
    assert body["summary"]["projects"] == 2
    assert [row["project"] for row in body["projects"]] == ["alpha", "beta"]
    assert body["hourly"]


def test_overview_unknown_range_is_422(api):
    assert api.get("/api/overview", params={"range": "Last decade"}).status_code == 422


def test_overview_empty_range_is_an_empty_state_not_an_error(api):
    # The seeded sessions are all from January 2024.
    response = api.get("/api/overview", params={"range": "Yesterday"})
    assert response.status_code == 200
    assert response.json() == {"range": "Yesterday", "empty": True}


def test_overview_project_order_is_shared_by_the_chart_arrays(api):
    body = api.get("/api/overview").json()
    assert body["project_order"] == [row["project"] for row in body["projects"]]


# ---------------------------------------------------------------- /api/sessions/{id}


def _assistant(message_id, *, new=0, read=0, written=0, tools=(), ts="2024-01-01T10:00:05Z"):
    return {
        "type": "assistant",
        "isSidechain": False,
        "timestamp": ts,
        "message": {
            "id": message_id,
            "model": "claude-sonnet-5",
            "content": [{"type": "tool_use", "name": name, "input": tool_input} for name, tool_input in tools],
            "usage": {
                "input_tokens": new,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": written,
                "output_tokens": 10,
            },
        },
    }


@pytest.fixture
def with_turns(isolated_db, write_config, write_transcript):
    """One session, aaa-1 in /h/alpha, with four assistant turns growing 50k -> 81k."""
    write_config(isolated_db / "claude.json", {})
    folder = claude_db.sanitize_project_path("/h/alpha")
    write_transcript(
        isolated_db / "projects" / folder / "aaa-1.jsonl",
        [
            {"type": "user", "timestamp": "2024-01-01T10:00:00Z", "cwd": "/h/alpha", "version": "1.0",
             "gitBranch": "main", "sessionId": "aaa-1", "message": {"content": "start"}},
            _assistant("m1", new=100, written=49_900, tools=[("Read", {"file_path": "a.py"})]),
            _assistant("m2", read=49_900, written=10_100, tools=[("Bash", {"command": "ls"})]),
            _assistant("m3", read=60_000, written=5_000),
            _assistant("m4", read=65_000, written=16_000),
        ],
    )
    claude_db.refresh()
    return isolated_db


def test_session_detail_has_a_recap_and_turns_that_reconcile(with_turns, monkeypatch):
    _use_live(monkeypatch)
    response = _client().get("/api/sessions/aaa-1")
    assert response.status_code == 200
    body = response.json()
    assert body["readable"] is True
    assert body["live"] is False
    assert body["recap"]["first_prompt"] == "start"
    assert body["recap"]["message_count"] == 5
    assert body["recap"]["context"] == 81_000

    turns = body["detail"]["turns"]
    assert [t["context"] for t in turns] == [50_000, 60_000, 65_000, 81_000]
    assert turns[0]["tools"] == [{"name": "Read", "hint": "a.py"}]
    attribution = body["detail"]["attribution"]
    assert attribution["floor"] == turns[0]["context"]
    assert attribution["current"] == turns[-1]["context"]
    assert attribution["floor"] + sum(g["tokens"] for g in attribution["by_tool"]) == attribution["current"]


def test_session_detail_for_a_live_session_is_flagged_and_uses_the_registry_cwd(with_turns, monkeypatch):
    _use_live(monkeypatch, [_live_session("aaa-1", cwd="/h/alpha")])
    body = _client().get("/api/sessions/aaa-1").json()
    assert body["live"] is True
    assert body["readable"] is True


def test_session_only_known_to_the_registry_gets_a_recap_from_it(isolated_db, monkeypatch):
    _use_live(monkeypatch, [_live_session("fresh-1")])
    body = _client().get("/api/sessions/fresh-1").json()
    assert body["live"] is True
    assert body["readable"] is False
    assert body["detail"] is None
    assert body["recap"]["message_count"] is None


def test_unreadable_transcript_is_readable_false_not_an_error(api, monkeypatch):
    monkeypatch.setattr(server.claude_context, "load_detail", lambda session_id, cwd: None)
    response = api.get("/api/sessions/aaa-1")
    assert response.status_code == 200
    body = response.json()
    assert body["readable"] is False
    assert body["detail"] is None
    assert body["recap"]["first_prompt"] == "fix the a.b thing"


def test_unknown_session_is_404(api):
    assert api.get("/api/sessions/nope-404").status_code == 404


# (A literal "../../x" isn't listed: HTTP clients collapse dot segments before sending,
# so it never arrives as a session ID. The encoded forms are what actually reach the route.)
@pytest.mark.parametrize("bad_id", ["a/b", "a%2Fb", "..%2F..%2Fx", "a.b", "a b", "x" * 65, "a\\b"])
def test_malformed_session_ids_are_rejected_before_any_filesystem_access(api, monkeypatch, bad_id):
    def boom(*args, **kwargs):
        raise AssertionError("the filesystem was touched")

    monkeypatch.setattr(server.claude_context, "load_detail", boom)
    monkeypatch.setattr(server.claude_context, "transcript_path", boom)
    monkeypatch.setattr(server.claude_transcripts, "delete_transcript", boom)
    monkeypatch.setattr(server.claude_db, "transcript_path_for_session", boom)
    for method in (api.get, api.delete):
        assert method(f"/api/sessions/{bad_id}").status_code in (404, 422)


def test_a_client_supplied_cwd_is_ignored(api, monkeypatch):
    seen = []

    def spy(session_id, cwd):
        seen.append(cwd)
        return None

    monkeypatch.setattr(server.claude_context, "load_detail", spy)
    api.get("/api/sessions/aaa-1", params={"cwd": "/etc"})
    assert seen == ["/h/alpha"]


# ---------------------------------------------------------------- DELETE /api/sessions/{id}


def test_deleting_a_live_session_is_409_and_keeps_the_file(seeded, monkeypatch):
    _use_live(monkeypatch, [_live_session("bbb-2")])
    path = claude_db.transcript_path_for_session("bbb-2")
    response = _client().delete("/api/sessions/bbb-2")
    assert response.status_code == 409
    assert path.exists()
    assert claude_db.transcript_path_for_session("bbb-2") is not None


def test_liveness_for_delete_is_a_fresh_read_not_the_cached_snapshot(seeded, monkeypatch):
    sessions = []
    monkeypatch.setattr(
        server, "live", LiveSnapshot(load_sessions=lambda: list(sessions), ttl=3600)
    )
    client = _client()
    assert client.get("/api/live").json() == {"sessions": []}  # the cache now says "nothing live"
    sessions.append(_live_session("bbb-2"))
    assert client.delete("/api/sessions/bbb-2").status_code == 409


def test_deleting_a_finished_session_removes_the_file_and_the_row(api):
    path = claude_db.transcript_path_for_session("bbb-2")
    response = api.delete("/api/sessions/bbb-2")
    assert response.status_code == 200
    assert not path.exists()
    assert "bbb-2" not in _ids(api.get("/api/transcripts"))
    assert api.delete("/api/sessions/bbb-2").status_code == 404


def test_deleting_an_unknown_session_is_404(api):
    assert api.delete("/api/sessions/nope-404").status_code == 404


# ---------------------------------------------------------------- /api/projects


@pytest.fixture
def with_projects(seeded, write_config, monkeypatch):
    write_config(
        seeded / "claude.json",
        {
            "/h/alpha": {"hasTrustDialogAccepted": True, "lastSessionId": "bbb-2", "mcpServers": {"gh": {}}},
            "/h/beta": {},
        },
    )
    claude_db.refresh()
    _use_live(monkeypatch)
    return _client()


def test_projects_lists_what_the_snapshot_knows(with_projects):
    body = with_projects.get("/api/projects").json()
    by_path = {p["path"]: p for p in body["projects"]}
    assert set(by_path) == {"/h/alpha", "/h/beta"}
    assert by_path["/h/alpha"]["name"] == "alpha"
    assert by_path["/h/alpha"]["trust_accepted"] is True
    assert by_path["/h/alpha"]["mcp_servers"] == ["gh"]


def test_deleting_a_project_removes_its_entry_and_transcripts(with_projects, seeded):
    alpha_files = [claude_db.transcript_path_for_session(s) for s in ("aaa-1", "bbb-2")]
    response = with_projects.delete("/api/projects", params={"path": "/h/alpha"})
    assert response.status_code == 200
    assert [p["path"] for p in with_projects.get("/api/projects").json()["projects"]] == ["/h/beta"]
    assert not any(path.exists() for path in alpha_files)
    assert _ids(with_projects.get("/api/transcripts")) == ["ccc-3"]
    assert "/h/alpha" not in (seeded / "claude.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("path", ["/h/alph", "/h/alpha/", "/h", "..", "/h/alpha/../beta", ""])
def test_a_project_path_not_in_the_snapshot_is_rejected_and_nothing_is_deleted(with_projects, seeded, path):
    files = [claude_db.transcript_path_for_session(s) for s in ("aaa-1", "bbb-2", "ccc-3")]
    config_before = (seeded / "claude.json").read_text(encoding="utf-8")
    response = with_projects.delete("/api/projects", params={"path": path})
    assert response.status_code == 404
    assert all(f.exists() for f in files)
    assert (seeded / "claude.json").read_text(encoding="utf-8") == config_before
    assert len(with_projects.get("/api/projects").json()["projects"]) == 2


def test_deleting_a_project_without_a_path_is_422(with_projects):
    assert with_projects.delete("/api/projects").status_code == 422
