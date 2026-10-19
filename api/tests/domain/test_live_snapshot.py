import json
from datetime import datetime, timezone

from app.domain.context.models import LiveContext
from app.repositories import claude_sessions
from app.repositories.claude_sessions import ClaudeSession
from app.domain.live_snapshot import LiveSnapshot


def _session(session_id="s1", pid=1, cwd="/x/proj"):
    return ClaudeSession(
        pid=pid, session_id=session_id, cwd=cwd, name="n", status="busy", kind="interactive",
        entrypoint="cli", version="2.0", started_at=datetime(2026, 1, 1, 9), updated_at=datetime(2026, 1, 1, 10),
        status_updated_at=None, raw={}, project="proj",
    )


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_context_carries_size_growth_history_and_formatted_label():
    snapshot = LiveSnapshot(
        load_sessions=lambda: [_session()],
        live_context=lambda sid, cwd: LiveContext(size=394_000, growth=2_100, history=[390_000, 394_000]),
    )
    context = snapshot.get()[0]["context"]
    assert context["size"] == 394_000
    assert context["growth"] == 2_100
    assert context["history"] == [390_000, 394_000]
    assert context["label"].startswith("394k ▲ +2.1k ")


def test_context_is_none_when_unavailable():
    snapshot = LiveSnapshot(load_sessions=lambda: [_session()], live_context=lambda sid, cwd: None)
    assert snapshot.get()[0]["context"] is None


def test_one_failing_context_read_leaves_other_sessions_populated():
    def fake_live_context(session_id, cwd):
        if session_id == "bad":
            raise RuntimeError("unreadable")
        return LiveContext(size=42_000, growth=None, history=[42_000])

    snapshot = LiveSnapshot(
        load_sessions=lambda: [_session("bad", pid=1), _session("good", pid=2)],
        live_context=fake_live_context,
    )
    items = snapshot.get()
    assert [i["session_id"] for i in items] == ["bad", "good"]
    assert items[0]["context"] is None
    assert items[1]["context"]["label"] == "42k"


def test_loader_runs_once_within_ttl_and_again_after_it_expires():
    calls = []
    clock = Clock()

    def loader():
        calls.append(1)
        return [_session()]

    snapshot = LiveSnapshot(load_sessions=loader, live_context=lambda s, c: None, ttl=1.0, clock=clock)
    for _ in range(20):
        snapshot.get()
    assert len(calls) == 1

    clock.now = 0.99
    snapshot.get()
    assert len(calls) == 1

    clock.now = 1.0
    snapshot.get()
    assert len(calls) == 2


def test_live_ids_come_from_the_same_snapshot():
    calls = []

    def loader():
        calls.append(1)
        return [_session("a", pid=1), _session("b", pid=2)]

    snapshot = LiveSnapshot(load_sessions=loader, live_context=lambda s, c: None, clock=Clock())
    snapshot.get()
    assert snapshot.live_ids() == {"a", "b"}
    assert len(calls) == 1


def test_empty_registry():
    snapshot = LiveSnapshot(load_sessions=lambda: [], live_context=lambda s, c: None)
    assert snapshot.get() == []


def test_latest_activity_uses_the_registry_cwd_for_a_live_session():
    seen = []
    stamp = datetime(2026, 1, 1, 12)

    def latest(session_id, cwd):
        seen.append((session_id, cwd))
        return stamp

    snapshot = LiveSnapshot(
        load_sessions=lambda: [_session("s1", cwd="/x/proj")], live_context=lambda s, c: None, latest_activity=latest
    )

    assert snapshot.latest_activity("s1") == stamp
    assert seen == [("s1", "/x/proj")]


def test_latest_activity_is_none_for_a_session_that_is_not_live():
    snapshot = LiveSnapshot(
        load_sessions=lambda: [_session("s1")],
        live_context=lambda s, c: None,
        latest_activity=lambda sid, cwd: datetime(2026, 1, 1),
    )
    assert snapshot.latest_activity("gone") is None


def test_items_carry_git_branch_and_default_to_empty():
    snapshot = LiveSnapshot(
        load_sessions=lambda: [_session("a", pid=1), _session("b", pid=2)],
        live_context=lambda sid, cwd: None,
        git_branches=lambda ids: {"a": "main"},
    )
    assert [i["git_branch"] for i in snapshot.get()] == ["main", ""]


def test_failing_branch_lookup_leaves_the_list_intact():
    def boom(ids):
        raise RuntimeError("snapshot missing")

    snapshot = LiveSnapshot(load_sessions=lambda: [_session()], live_context=lambda sid, cwd: None, git_branches=boom)
    items = snapshot.get()
    assert [i["session_id"] for i in items] == ["s1"]
    assert items[0]["git_branch"] == ""


def _compact_snapshot(now, latest_compaction=lambda sid, cwd: None, clock=None):
    return LiveSnapshot(
        load_sessions=lambda: [_session()],
        live_context=lambda sid, cwd: None,
        latest_compaction=latest_compaction,
        ttl=1.0,
        clock=clock or Clock(),
        now=now,
    )


def test_compact_grade_runs_from_the_start_and_carries_the_anchor():
    snapshot = _compact_snapshot(lambda: datetime(2026, 1, 1, 9, 50).astimezone())
    compact = snapshot.get()[0]["compact"]
    assert compact["state"] == "should"
    assert compact["since"] == datetime(2026, 1, 1, 9).astimezone().astimezone(timezone.utc).isoformat()


def test_a_reopened_session_is_graded_from_its_conversations_start(tmp_path, monkeypatch):
    now = datetime(2026, 1, 1, 10, 50, tzinfo=timezone.utc)
    conversation_start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    reopened_at = datetime(2026, 1, 1, 10, 48, tzinfo=timezone.utc)

    class Transcript:
        session_id = "s1"
        project = title = last_message = first_prompt = ""
        started_at = conversation_start

    monkeypatch.setattr(claude_sessions, "load_transcripts", lambda: [Transcript()])
    (tmp_path / "1.json").write_text(
        json.dumps({"pid": 1, "sessionId": "s1", "startedAt": reopened_at.timestamp() * 1000}),
        encoding="utf-8",
    )
    snapshot = LiveSnapshot(
        load_sessions=lambda: claude_sessions.load_sessions(tmp_path),
        live_context=lambda sid, cwd: None,
        latest_compaction=lambda sid, cwd: None,
        ttl=1.0,
        clock=Clock(),
        now=lambda: now,
    )

    item = snapshot.get()[0]
    assert item["started_at"] == conversation_start.isoformat()
    assert item["compact"]["state"] == "should"


def test_a_compaction_after_the_start_restarts_the_clock():
    snapshot = _compact_snapshot(
        lambda: datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        latest_compaction=lambda sid, cwd: datetime(2026, 1, 1, 11, 55, tzinfo=timezone.utc),
    )
    assert snapshot.get()[0]["compact"]["state"] == "ok"


def test_a_failing_compaction_lookup_falls_back_to_the_start_and_keeps_the_row():
    def broken(sid, cwd):
        raise RuntimeError("unreadable")

    snapshot = _compact_snapshot(lambda: datetime(2026, 1, 1, 12).astimezone(), latest_compaction=broken)
    item = snapshot.get()[0]
    assert item["compact"]["state"] == "needs"
    assert item["session_id"] == "s1"


def test_the_grade_moves_on_without_new_activity_once_the_ttl_passes():
    clock = Clock()
    now = [datetime(2026, 1, 1, 9, 44).astimezone()]
    snapshot = _compact_snapshot(lambda: now[0], clock=clock)
    assert snapshot.get()[0]["compact"]["state"] == "ok"
    now[0] = datetime(2026, 1, 1, 9, 46).astimezone()
    clock.now = 2.0
    assert snapshot.get()[0]["compact"]["state"] == "should"
