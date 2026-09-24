"""The data endpoints (/api/live, /api/transcripts, ...) over throwaway ~/.claude fixtures."""

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import claude_db
import server
from claude_context import LiveContext
from claude_sessions import ClaudeSession
from live_snapshot import LiveSnapshot
from pending_decisions import PendingDecisions


def _client():
    """A client the security middleware treats as the browser on this machine."""
    return TestClient(
        server.app,
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
        headers={"X-Requested-With": "ledger"},
    )


TOKEN = "s3cret-token-value_0123456789"
BEARER = {"Authorization": f"Bearer {TOKEN}"}


def _remote_client(*, token=True, csrf=True):
    """A phone on the LAN, by default carrying the access token (set `server.access_token` to
    TOKEN first) and the custom header every non-GET request needs."""
    return TestClient(
        server.app,
        base_url="http://192.168.1.20:8501",
        client=("192.168.1.50", 5000),
        headers={**(BEARER if token else {}), **({"X-Requested-With": "ledger"} if csrf else {})},
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
    assert body["sessions"][0]["pending_decision"] is None


def test_live_with_nothing_running_is_an_empty_list(isolated_db, monkeypatch):
    _use_live(monkeypatch)
    assert _client().get("/api/live").json() == {"sessions": []}


def test_live_reflects_a_pending_decision(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    _use_live(monkeypatch, [_live_session("live-1")])
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})

    body = _client().get("/api/live").json()

    assert body["sessions"][0]["pending_decision"] == {
        "id": prompt_id, "tool_name": "Bash", "tool_input": {"command": "ls"},
    }


def test_live_shows_the_oldest_prompt_first(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    _use_live(monkeypatch, [_live_session("live-1")])
    first = store.register("live-1", "Bash", {"command": "first"})
    store.register("live-1", "Bash", {"command": "second"})

    assert _client().get("/api/live").json()["sessions"][0]["pending_decision"]["id"] == first


def test_live_hides_prompts_from_another_device_unless_remote_mode_is_on(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    _use_live(monkeypatch, [_live_session("live-1")])
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})

    off = _remote_client().get("/api/live").json()
    assert off["sessions"][0]["pending_decision"] is None
    assert _client().get("/api/live").json()["sessions"][0]["pending_decision"]["id"] == prompt_id

    store.set_remote_mode(True)
    on = _remote_client().get("/api/live").json()
    assert on["sessions"][0]["pending_decision"]["id"] == prompt_id


def test_live_drops_a_prompt_once_its_transcript_moved_on(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    later = datetime.now(timezone.utc) + timedelta(seconds=30)
    monkeypatch.setattr(
        server, "live",
        LiveSnapshot(load_sessions=lambda: [_live_session("live-1")], latest_activity=lambda sid, cwd: later),
    )
    store.register("live-1", "Bash", {"command": "ls"})

    assert _client().get("/api/live").json()["sessions"][0]["pending_decision"] is None
    assert store.for_session("live-1") == []


# ---------------------------------------------------------------- POST /api/sessions/{id}/decisions

QUESTION_INPUT = {
    "questions": [
        {"question": "Which db?", "options": [{"label": "sqlite"}, {"label": "postgres"}], "multiSelect": False},
        {"question": "Which extras?", "options": [{"label": "auth"}, {"label": "logs"}], "multiSelect": True},
    ]
}


def _start_hook(store, tool_name="Bash", tool_input=None, session_id="live-1"):
    """The relay hook's request, on its own thread (it blocks until the prompt resolves).

    Returns `(thread, result, prompt)` once the prompt is registered; result["response"] is
    filled in when the request returns.
    """
    result = {}

    def run():
        result["response"] = _client().post(
            f"/api/sessions/{session_id}/decisions",
            json={"tool_name": tool_name, "tool_input": tool_input or {"command": "ls"}},
        )

    thread = threading.Thread(target=run)
    thread.start()
    deadline = time.monotonic() + 5
    while not store.for_session(session_id):
        assert time.monotonic() < deadline, "the hook's request never registered a prompt"
        time.sleep(0.01)
    return thread, result, store.for_session(session_id)[0]


def _answer(session_id, prompt_id, body, client=None):
    return (client or _client()).post(f"/api/sessions/{session_id}/decisions/{prompt_id}/answer", json=body)


def test_decisions_answered_returns_the_answer_to_the_hook(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    _use_live(monkeypatch, [_live_session("live-1")])
    thread, result, prompt = _start_hook(store)
    assert prompt["tool_name"] == "Bash" and prompt["tool_input"] == {"command": "ls"}

    assert _answer("live-1", prompt["id"], {"decision": "allow"}).status_code == 200
    thread.join(5)

    assert result["response"].status_code == 200
    assert result["response"].json() == {"decision": "allow"}
    assert store.for_session("live-1") == []


def test_decisions_cleared_without_an_answer_returns_no_decision(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    thread, result, prompt = _start_hook(store)

    store.clear("live-1", prompt["id"])
    thread.join(5)

    assert result["response"].status_code == 200
    assert result["response"].json() == {"decision": None}


def test_decisions_wait_elapsing_returns_no_decision(isolated_db, monkeypatch):
    store = PendingDecisions(max_age=0.2)
    monkeypatch.setattr(server, "decisions", store)

    response = _client().post(
        "/api/sessions/live-1/decisions", json={"tool_name": "Bash", "tool_input": {"command": "ls"}}
    )

    assert response.status_code == 200
    assert response.json() == {"decision": None}
    assert store.for_session("live-1") == []


def test_decisions_are_only_registered_by_a_local_request(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)

    response = _remote_client().post(
        "/api/sessions/live-1/decisions", json={"tool_name": "Bash", "tool_input": {"command": "ls"}}
    )

    assert response.status_code == 403
    assert store.for_session("live-1") == []


# ---------------------------------------------------------------- GET /api/sessions/{id}/pending-decision


def test_pending_decision_endpoint_reports_none(isolated_db, monkeypatch):
    monkeypatch.setattr(server, "decisions", PendingDecisions())
    assert _client().get("/api/sessions/live-1/pending-decision").json() == {"pending_decision": None}


def test_pending_decision_endpoint_reports_the_oldest_prompt(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    first = store.register("live-1", "Edit", {"file": "a.py"})
    store.register("live-1", "Edit", {"file": "b.py"})

    body = _client().get("/api/sessions/live-1/pending-decision").json()

    assert body == {"pending_decision": {"id": first, "tool_name": "Edit", "tool_input": {"file": "a.py"}}}


def test_pending_decision_endpoint_follows_the_visibility_rule(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})

    # Local: always visible. Another device: only while Remote mode is on.
    assert _client().get("/api/sessions/live-1/pending-decision").json()["pending_decision"]["id"] == prompt_id
    assert _remote_client().get("/api/sessions/live-1/pending-decision").json() == {"pending_decision": None}
    store.set_remote_mode(True)
    assert _remote_client().get("/api/sessions/live-1/pending-decision").json()["pending_decision"]["id"] == prompt_id


# ---------------------------------------------------------------- POST /api/sessions/{id}/decisions/{prompt_id}/answer


@pytest.mark.parametrize(
    "tool_name, tool_input, body, expected",
    [
        ("Bash", {"command": "ls"}, {"decision": "allow"}, {"decision": "allow"}),
        ("Bash", {"command": "rm"}, {"decision": "deny"}, {"decision": "deny", "reason": None}),
        ("Bash", {"command": "rm"}, {"decision": "deny", "reason": "  "}, {"decision": "deny", "reason": None}),
        ("Bash", {"command": "rm"}, {"decision": "deny", "reason": "not now"},
         {"decision": "deny", "reason": "not now"}),
        # an option label, free text ("Other") and a multi-select array, all as sent
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": "postgres", "Which extras?": ["auth", "logs"]}},
         {"decision": "answer", "answers": {"Which db?": "postgres", "Which extras?": ["auth", "logs"]}}),
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": "duckdb, actually", "Which extras?": "metrics"}},
         {"decision": "answer", "answers": {"Which db?": "duckdb, actually", "Which extras?": "metrics"}}),
    ],
    ids=["allow", "deny", "deny-blank-reason", "deny-reason", "question-label-and-multi", "question-free-text"],
)
def test_answer_resolves_the_hook_with_each_shape(isolated_db, monkeypatch, tool_name, tool_input, body, expected):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    _use_live(monkeypatch, [_live_session("live-1")])
    thread, result, prompt = _start_hook(store, tool_name, tool_input)

    response = _answer("live-1", prompt["id"], body)
    thread.join(5)

    assert response.status_code == 200
    assert response.json() == {"answered": prompt["id"]}
    assert result["response"].json() == expected


@pytest.mark.parametrize(
    "tool_name, tool_input, body",
    [
        ("Bash", {"command": "ls"}, {"decision": "answer", "answers": {"x": "y"}}),
        ("AskUserQuestion", QUESTION_INPUT, {"decision": "allow"}),
        ("AskUserQuestion", QUESTION_INPUT, {"decision": "deny"}),
        ("AskUserQuestion", QUESTION_INPUT, {"decision": "answer"}),
        # a question that was never asked / one left unanswered
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": "sqlite", "Which extras?": "auth", "Nope?": "x"}}),
        ("AskUserQuestion", QUESTION_INPUT, {"decision": "answer", "answers": {"Which db?": "sqlite"}}),
        # an array for a single-select question
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": ["sqlite"], "Which extras?": ["auth"]}}),
        # blank text, blank/empty selections
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": "  ", "Which extras?": ["auth"]}}),
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": "sqlite", "Which extras?": []}}),
        ("AskUserQuestion", QUESTION_INPUT,
         {"decision": "answer", "answers": {"Which db?": "sqlite", "Which extras?": [" "]}}),
        # a prompt that carries no questions at all
        ("AskUserQuestion", {}, {"decision": "answer", "answers": {"Which db?": "sqlite"}}),
    ],
    ids=["answer-to-permission", "allow-a-question", "deny-a-question", "no-answers", "unknown-question",
         "missing-question", "list-for-single-select", "blank-text", "empty-list", "blank-list-item", "no-questions"],
)
def test_an_answer_that_does_not_fit_the_prompt_is_422_and_leaves_it_pending(
    isolated_db, monkeypatch, tool_name, tool_input, body
):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    prompt_id = store.register("live-1", tool_name, tool_input)

    response = _answer("live-1", prompt_id, body)

    assert response.status_code == 422
    assert [p["id"] for p in store.for_session("live-1")] == [prompt_id]


def test_answer_is_409_when_the_prompt_is_gone(isolated_db, monkeypatch):
    monkeypatch.setattr(server, "decisions", PendingDecisions())
    assert _answer("live-1", "deadbeef", {"decision": "allow"}).status_code == 409


def test_answer_is_409_for_an_already_answered_prompt(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})

    assert _answer("live-1", prompt_id, {"decision": "allow"}).status_code == 200
    assert _answer("live-1", prompt_id, {"decision": "deny"}).status_code == 409


def test_answer_is_409_when_the_session_moved_on_in_the_terminal(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    later = datetime.now(timezone.utc) + timedelta(seconds=30)
    monkeypatch.setattr(
        server, "live",
        LiveSnapshot(load_sessions=lambda: [_live_session("live-1")], latest_activity=lambda sid, cwd: later),
    )
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})

    assert _answer("live-1", prompt_id, {"decision": "allow"}).status_code == 409


def test_answer_names_its_own_prompt_when_two_are_open(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    first = store.register("live-1", "Bash", {"command": "one"})
    second = store.register("live-1", "Bash", {"command": "two"})

    assert _answer("live-1", second, {"decision": "allow"}).status_code == 200
    assert [p["id"] for p in store.for_session("live-1")] == [first]


def test_answer_from_another_device_needs_remote_mode(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})
    body = {"decision": "allow"}

    off = _answer("live-1", prompt_id, body, client=_remote_client())
    assert off.status_code == 403
    assert [p["id"] for p in store.for_session("live-1")] == [prompt_id]

    store.set_remote_mode(True)
    on = _answer("live-1", prompt_id, body, client=_remote_client())
    assert on.status_code == 200
    assert store.for_session("live-1") == []


def test_answer_from_another_device_still_needs_the_token_and_csrf_header(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    store.set_remote_mode(True)
    prompt_id = store.register("live-1", "Bash", {"command": "ls"})
    url = f"/api/sessions/live-1/decisions/{prompt_id}/answer"

    no_token = _remote_client(token=False)
    no_header = _remote_client(csrf=False)
    assert no_token.post(url, json={"decision": "allow"}).status_code == 401
    assert no_header.post(url, json={"decision": "allow"}).status_code == 403
    assert [p["id"] for p in store.for_session("live-1")] == [prompt_id]


# ---------------------------------------------------------------- Remote mode: GET /api/meta + POST /api/remote-mode


def test_meta_reports_remote_mode_off_by_default(isolated_db, monkeypatch):
    monkeypatch.setattr(server, "decisions", PendingDecisions())
    assert _client().get("/api/meta").json()["remote_mode"] == {"enabled": False, "expires_at": None}


def test_a_local_request_switches_remote_mode_without_a_token(isolated_db, monkeypatch):
    monkeypatch.setattr(server, "decisions", PendingDecisions())
    client = _client()

    on = client.post("/api/remote-mode", json={"enabled": True})
    assert on.status_code == 200
    assert on.json()["enabled"] is True and on.json()["expires_at"]
    assert client.get("/api/meta").json()["remote_mode"] == on.json()

    off = client.post("/api/remote-mode", json={"enabled": False})
    assert off.json() == {"enabled": False, "expires_at": None}
    assert client.get("/api/meta").json()["remote_mode"] == off.json()


def test_a_remote_request_with_a_valid_token_cannot_switch_remote_mode(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    remote = _remote_client()

    assert remote.post("/api/remote-mode", json={"enabled": True}).status_code == 403
    assert store.remote_mode()["enabled"] is False

    store.set_remote_mode(True)
    assert remote.post("/api/remote-mode", json={"enabled": False}).status_code == 403
    assert store.remote_mode()["enabled"] is True


def test_a_remote_request_without_the_token_cannot_switch_remote_mode(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    client = _remote_client(token=False)

    assert client.post("/api/remote-mode", json={"enabled": True}).status_code == 401
    assert store.remote_mode()["enabled"] is False


def test_meta_shows_another_device_the_remote_mode_state(isolated_db, monkeypatch):
    store = PendingDecisions()
    monkeypatch.setattr(server, "decisions", store)
    monkeypatch.setattr(server, "access_token", TOKEN)
    store.set_remote_mode(True)

    meta = _remote_client().get("/api/meta").json()

    assert meta["is_local"] is False
    assert meta["remote_mode"] == store.remote_mode() and meta["remote_mode"]["enabled"] is True


# ---------------------------------------------------------------- POST /api/sessions/{id}/open-repo


def test_open_repo_invokes_the_script_with_the_registry_cwd(isolated_db, monkeypatch):
    _use_live(monkeypatch, [_live_session("live-1", cwd="/h/alpha")])
    calls = []
    monkeypatch.setattr(server.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    response = _client().post("/api/sessions/live-1/open-repo")

    assert response.status_code == 200
    assert response.json() == {"opened": "live-1"}
    assert len(calls) == 1
    (command,), kwargs = calls[0]
    assert command[0] == "powershell.exe"
    assert command[-2] == str(server.OPEN_REPO_SCRIPT)
    assert command[-1] == "claudecode://open?path=%2Fh%2Falpha"
    assert kwargs == {"check": False}


def test_open_repo_is_404_for_an_unknown_or_not_live_session(isolated_db, monkeypatch):
    _use_live(monkeypatch)
    calls = []
    monkeypatch.setattr(server.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    response = _client().post("/api/sessions/nope-1/open-repo")

    assert response.status_code == 404
    assert calls == []


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
