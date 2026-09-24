import asyncio

from pending_decisions import PendingDecisions


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_unwatched_session_returns_no_opinion_immediately():
    store = PendingDecisions(clock=Clock())

    result = asyncio.run(store.request_decision("s1", "Bash", {"command": "ls"}))

    assert result == {"decision": None, "reason": None}
    assert store.peek("s1") is None


def test_watched_session_registers_then_resolves_on_answer():
    store = PendingDecisions(clock=Clock(), wait_timeout=5.0)
    store.touch_watch("s1")

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {"command": "ls"}))
        await asyncio.sleep(0)  # let request_decision register before answering
        assert store.peek("s1") == {"tool_name": "Bash", "tool_input": {"command": "ls"}}
        assert store.answer("s1", "allow") is True
        return await task

    result = asyncio.run(run())

    assert result == {"decision": "allow", "reason": None}
    assert store.peek("s1") is None


def test_watched_session_carries_a_deny_reason():
    store = PendingDecisions(clock=Clock(), wait_timeout=5.0)
    store.touch_watch("s1")

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Edit", {"file": "x.py"}))
        await asyncio.sleep(0)
        store.answer("s1", "deny", "not now")
        return await task

    result = asyncio.run(run())

    assert result == {"decision": "deny", "reason": "not now"}


def test_watched_session_times_out_and_passes_through():
    store = PendingDecisions(clock=Clock(), wait_timeout=0.05)
    store.touch_watch("s1")

    result = asyncio.run(store.request_decision("s1", "Bash", {"command": "ls"}))

    assert result == {"decision": None, "reason": None}
    assert store.peek("s1") is None


def test_answer_returns_false_when_nothing_pending():
    store = PendingDecisions()
    assert store.answer("nope", "allow") is False


def test_answer_returns_false_once_already_answered():
    store = PendingDecisions(clock=Clock(), wait_timeout=5.0)
    store.touch_watch("s1")

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {"command": "ls"}))
        await asyncio.sleep(0)
        first = store.answer("s1", "allow")
        await task
        second = store.answer("s1", "deny")
        return first, second

    first, second = asyncio.run(run())

    assert first is True
    assert second is False


def test_touch_watch_expires_after_the_window():
    clock = Clock()
    store = PendingDecisions(watch_window=5.0, clock=clock)
    store.touch_watch("s1")
    assert store.is_watched("s1") is True

    clock.now = 4.99
    assert store.is_watched("s1") is True

    clock.now = 5.0
    assert store.is_watched("s1") is False


def test_is_watched_false_for_unknown_session():
    store = PendingDecisions()
    assert store.is_watched("nope") is False


def test_one_session_pending_does_not_affect_another():
    store = PendingDecisions(clock=Clock(), wait_timeout=5.0)
    store.touch_watch("a")
    store.touch_watch("b")

    async def run():
        task_a = asyncio.create_task(store.request_decision("a", "Bash", {}))
        task_b = asyncio.create_task(store.request_decision("b", "Edit", {}))
        await asyncio.sleep(0)
        store.answer("a", "allow")
        result_a = await task_a
        assert store.peek("b") == {"tool_name": "Edit", "tool_input": {}}
        store.answer("b", "deny", "no")
        result_b = await task_b
        return result_a, result_b

    result_a, result_b = asyncio.run(run())

    assert result_a == {"decision": "allow", "reason": None}
    assert result_b == {"decision": "deny", "reason": "no"}
