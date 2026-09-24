"""hooks/ledgerScripts/Relay-PermissionRequest.ps1, run for real against a real API server.

The unit and TestClient tests cover the API's half of the remote-session-control change; this covers
the other half, the script Claude Code actually runs, and the guarantee everything else rests on:
whatever happens, a hook with no answer prints NOTHING (any output is a decision) and exits 0, so
the terminal dialog stays the only way to answer. Each test starts uvicorn on a free loopback port
in this process and runs the script as a subprocess, exactly as Claude Code does (JSON on stdin,
decision JSON on stdout).

Windows PowerShell only, like every other file under hooks/.
"""

import json
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import uvicorn

import server
from claude_sessions import ClaudeSession
from live_snapshot import LiveSnapshot
from pending_decisions import PendingDecisions

pytestmark = pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="the relay hook is a Windows PowerShell script",
)

SCRIPT = Path(__file__).resolve().parents[2] / "hooks" / "ledgerScripts" / "Relay-PermissionRequest.ps1"
SESSION = "live-1"
CSRF = {"X-Requested-With": "ledger"}

QUESTIONS = {
    "questions": [
        {"question": "Which db?", "options": [{"label": "sqlite"}, {"label": "postgres"}], "multiSelect": False},
        {"question": "Which extras?", "options": [{"label": "auth"}, {"label": "logs"}], "multiSelect": True},
    ]
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _Api:
    """A real uvicorn server for `server.app` on a loopback port, with a fresh prompt store."""

    def __init__(self, monkeypatch, *, max_age: float = 60.0):
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.store = PendingDecisions(max_age=max_age)
        self.activity: dict[str, datetime] = {}
        monkeypatch.setattr(server, "decisions", self.store)
        monkeypatch.setattr(
            server,
            "live",
            LiveSnapshot(
                load_sessions=lambda: [_session(SESSION)],
                live_context=lambda session_id, cwd: None,
                latest_activity=lambda session_id, cwd: self.activity.get(session_id),
            ),
        )
        config = uvicorn.Config(
            server.app, host="127.0.0.1", port=self.port, lifespan="off", log_level="warning"
        )
        self._uvicorn = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._uvicorn.run, daemon=True)

    def start(self) -> "_Api":
        self._thread.start()
        deadline = time.monotonic() + 10
        while not self._uvicorn.started:
            assert time.monotonic() < deadline, "the test API server never started"
            time.sleep(0.02)
        return self

    def stop(self) -> None:
        self._uvicorn.should_exit = True
        self._thread.join(10)

    def prompts(self, count: int = 1, session_id: str = SESSION, timeout: float = 30.0) -> list[dict]:
        """Wait until `count` prompts are registered for the session (the hook process needs a moment
        to start), then return them oldest first."""
        deadline = time.monotonic() + timeout
        while len(self.store.for_session(session_id)) < count:
            assert time.monotonic() < deadline, f"only {len(self.store.for_session(session_id))} prompt(s) registered"
            time.sleep(0.05)
        return self.store.for_session(session_id)

    def answer(self, prompt_id: str, body: dict, session_id: str = SESSION) -> httpx.Response:
        return httpx.post(
            f"{self.url}/api/sessions/{session_id}/decisions/{prompt_id}/answer", json=body, headers=CSRF
        )


def _session(session_id: str) -> ClaudeSession:
    return ClaudeSession(
        pid=7, session_id=session_id, cwd="/h/alpha", name="n", status="busy", kind="interactive",
        entrypoint="cli", version="2", started_at=datetime(2024, 1, 1, 9), updated_at=datetime(2024, 1, 1, 10),
        status_updated_at=None, raw={}, project="alpha",
    )


@pytest.fixture
def api(monkeypatch):
    instance = _Api(monkeypatch).start()
    yield instance
    instance.stop()


class _Hook:
    """One run of the relay script; `result()` waits for it and returns (stdout, exit code)."""

    def __init__(self, payload, *, port: int, timeout_seconds: int = 60):
        stdin = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        self._process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
             "-Port", str(port), "-TimeoutSeconds", str(timeout_seconds)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self._process.stdin.write(stdin)
        self._process.stdin.close()

    def result(self, timeout: float = 60.0) -> tuple[str, int]:
        try:
            out, _ = self._process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            raise
        return out.decode("utf-8"), self._process.returncode

    def decision(self, timeout: float = 60.0) -> dict:
        out, code = self.result(timeout)
        assert code == 0
        output = json.loads(out)["hookSpecificOutput"]
        assert output["hookEventName"] == "PermissionRequest"
        return output["decision"]


def _payload(tool_name="Bash", tool_input=None, session_id=SESSION):
    return {
        "session_id": session_id, "cwd": "/h/alpha", "tool_name": tool_name,
        "tool_input": {"command": "ls"} if tool_input is None else tool_input,
    }


# ---------------------------------------------------------------- answers become decisions


def test_approve_prints_an_allow_decision(api):
    hook = _Hook(_payload(), port=api.port)
    prompt = api.prompts()[0]
    assert (prompt["tool_name"], prompt["tool_input"]) == ("Bash", {"command": "ls"})

    assert api.answer(prompt["id"], {"decision": "allow"}).status_code == 200

    assert hook.decision() == {"behavior": "allow"}
    assert api.store.for_session(SESSION) == []


def test_deny_prints_the_reason_as_the_message(api):
    hook = _Hook(_payload(), port=api.port)
    prompt = api.prompts()[0]

    api.answer(prompt["id"], {"decision": "deny", "reason": "not on prod"})

    assert hook.decision() == {"behavior": "deny", "message": "not on prod"}


def test_deny_without_a_reason_still_prints_a_message(api):
    hook = _Hook(_payload(), port=api.port)
    prompt = api.prompts()[0]

    api.answer(prompt["id"], {"decision": "deny"})

    decision = hook.decision()
    assert decision["behavior"] == "deny"
    assert decision["message"]


def test_a_question_answer_becomes_updated_input_with_the_original_questions(api):
    hook = _Hook(_payload("AskUserQuestion", QUESTIONS), port=api.port)
    prompt = api.prompts()[0]

    answers = {"Which db?": "postgres", "Which extras?": ["auth", "logs"]}
    assert api.answer(prompt["id"], {"decision": "answer", "answers": answers}).status_code == 200

    decision = hook.decision()
    assert decision["behavior"] == "allow"
    assert decision["updatedInput"]["questions"] == QUESTIONS["questions"]
    assert decision["updatedInput"]["answers"] == answers
    assert decision["updatedInput"]["annotations"] == {}


def test_a_single_item_multi_select_answer_stays_a_list(api):
    # PowerShell 5.1's JSON round trip is prone to collapsing one-element arrays into scalars.
    hook = _Hook(_payload("AskUserQuestion", QUESTIONS), port=api.port)
    prompt = api.prompts()[0]

    answers = {"Which db?": "sqlite", "Which extras?": ["auth"]}
    api.answer(prompt["id"], {"decision": "answer", "answers": answers})

    assert hook.decision()["updatedInput"]["answers"]["Which extras?"] == ["auth"]


def test_non_ascii_survives_both_directions(api):
    tool_input = {
        "questions": [{"question": "Welche Datenbank? ✓", "options": [{"label": "Käse"}], "multiSelect": False}]
    }
    hook = _Hook(_payload("AskUserQuestion", tool_input), port=api.port)
    prompt = api.prompts()[0]
    assert prompt["tool_input"] == tool_input  # the API got exactly what the tool sent

    api.answer(prompt["id"], {"decision": "answer", "answers": {"Welche Datenbank? ✓": "Käse — 日本語"}})

    out, code = hook.result()
    assert code == 0
    assert out.isascii()  # safe under whatever code page stdout uses
    assert json.loads(out)["hookSpecificOutput"]["decision"]["updatedInput"]["answers"] == {
        "Welche Datenbank? ✓": "Käse — 日本語"
    }


# ---------------------------------------------------------------- silence: never alter the terminal


def test_a_stopped_backend_is_silent_and_immediate(monkeypatch):
    port = _free_port()  # nothing listening on it
    started = time.monotonic()

    out, code = _Hook(_payload(), port=port).result(timeout=30)

    assert (out, code) == ("", 0)
    # A dialog must not wait on a backend that isn't there; the bulk of this is PowerShell start-up.
    assert time.monotonic() - started < 10


def test_the_terminal_answering_first_releases_the_hook_silently(api):
    hook = _Hook(_payload(), port=api.port)
    prompt = api.prompts()[0]
    assert httpx.get(f"{api.url}/api/live").json()["sessions"][0]["pending_decision"]["id"] == prompt["id"]

    # The person answers in the terminal: the transcript gets the tool result.
    api.activity[SESSION] = datetime.now(timezone.utc) + timedelta(seconds=5)
    live = httpx.get(f"{api.url}/api/live").json()  # the poll runs the sweep

    assert live["sessions"][0]["pending_decision"] is None
    assert hook.result() == ("", 0)
    # ...and a dashboard answer that arrives late is refused without touching the session.
    assert api.answer(prompt["id"], {"decision": "allow"}).status_code == 409


def test_a_prompt_outliving_the_max_age_is_silent(monkeypatch):
    api = _Api(monkeypatch, max_age=1.0).start()
    try:
        assert _Hook(_payload(), port=api.port).result() == ("", 0)
        assert api.store.for_session(SESSION) == []
    finally:
        api.stop()


def test_the_hook_giving_up_first_is_silent(api):
    # The client-side timeout elapsing (the API is still waiting) must not print a decision.
    assert _Hook(_payload(), port=api.port, timeout_seconds=1).result() == ("", 0)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"not json",
        json.dumps({"session_id": SESSION, "tool_input": {}}).encode(),  # no tool_name
        json.dumps(_payload(session_id="../../etc")).encode(),  # not a routable session id
        json.dumps(_payload(session_id="")).encode(),
    ],
)
def test_a_bad_payload_is_silent_and_registers_nothing(api, payload):
    assert _Hook(payload, port=api.port).result() == ("", 0)
    assert api.store.for_session(SESSION) == []


# ---------------------------------------------------------------- arbitration


def test_two_prompts_for_one_session_each_get_their_own_answer(api):
    first = _Hook(_payload(tool_input={"command": "first"}), port=api.port)
    api.prompts(1)
    second = _Hook(_payload(tool_input={"command": "second"}), port=api.port)
    prompts = {p["tool_input"]["command"]: p for p in api.prompts(2)}

    # Answer them in the opposite order to how they arrived, one allow and one deny.
    api.answer(prompts["second"]["id"], {"decision": "deny", "reason": "no to second"})
    api.answer(prompts["first"]["id"], {"decision": "allow"})

    assert first.decision() == {"behavior": "allow"}
    assert second.decision() == {"behavior": "deny", "message": "no to second"}


def test_a_dashboard_answer_for_one_session_leaves_another_waiting(api, monkeypatch):
    other = "live-2"
    hook_one = _Hook(_payload(), port=api.port)
    hook_two = _Hook(_payload(session_id=other), port=api.port)
    prompt_one = api.prompts(1, SESSION)[0]
    api.prompts(1, other)

    api.answer(prompt_one["id"], {"decision": "allow"})

    assert hook_one.decision() == {"behavior": "allow"}
    assert len(api.store.for_session(other)) == 1
    api.answer(api.store.for_session(other)[0]["id"], {"decision": "deny", "reason": "x"}, session_id=other)
    assert hook_two.decision() == {"behavior": "deny", "message": "x"}
