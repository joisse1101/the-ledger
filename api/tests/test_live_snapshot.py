from datetime import datetime

from claude_context import LiveContext
from claude_sessions import ClaudeSession
from live_snapshot import LiveSnapshot


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
