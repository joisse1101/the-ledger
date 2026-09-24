import asyncio
import threading
from datetime import datetime, timedelta, timezone

import claude_context
from pending_decisions import PendingDecisions

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class Clock:
    """One fake time source for both the monotonic and the wall clock the store takes."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def wall(self):
        return T0 + timedelta(seconds=self.now)


def make_store(clock=None, **kwargs):
    clock = clock or Clock()
    return PendingDecisions(clock=clock, wall_clock=clock.wall, **kwargs), clock


def never_active(_session_id):
    return None


# ---------------------------------------------------------------- register / answer / resolve


def test_register_then_answer_resolves_the_waiter():
    store, _ = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {"command": "ls"}))
        await asyncio.sleep(0)  # let request_decision register before answering
        pending = store.peek("s1")
        assert pending["tool_name"] == "Bash"
        assert pending["tool_input"] == {"command": "ls"}
        assert store.answer("s1", pending["id"], {"decision": "allow"}) is True
        return await task

    assert asyncio.run(run()) == {"decision": "allow"}
    assert store.peek("s1") is None


def test_answer_carries_a_deny_reason_and_question_answers():
    store, _ = make_store()

    async def run():
        deny = asyncio.create_task(store.request_decision("s1", "Edit", {"file": "x.py"}))
        ask = asyncio.create_task(store.request_decision("s2", "AskUserQuestion", {"questions": []}))
        await asyncio.sleep(0)
        store.answer("s1", store.peek("s1")["id"], {"decision": "deny", "reason": "not now"})
        store.answer("s2", store.peek("s2")["id"], {"decision": "answer", "answers": {"Which?": "A"}})
        return await deny, await ask

    deny, ask = asyncio.run(run())

    assert deny == {"decision": "deny", "reason": "not now"}
    assert ask == {"decision": "answer", "answers": {"Which?": "A"}}


def test_answer_is_false_for_an_unknown_or_already_answered_prompt():
    store, _ = make_store()
    assert store.answer("nope", "missing", {"decision": "allow"}) is False

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        prompt_id = store.peek("s1")["id"]
        first = store.answer("s1", prompt_id, {"decision": "allow"})
        await task
        second = store.answer("s1", prompt_id, {"decision": "deny"})
        return first, second

    assert asyncio.run(run()) == (True, False)


def test_two_prompts_for_one_session_keep_independent_ids():
    store, _ = make_store()

    async def run():
        first = asyncio.create_task(store.request_decision("s1", "Bash", {"command": "a"}))
        await asyncio.sleep(0)
        second = asyncio.create_task(store.request_decision("s1", "Bash", {"command": "b"}))
        await asyncio.sleep(0)

        pending = store.for_session("s1")
        assert [p["tool_input"]["command"] for p in pending] == ["a", "b"]  # oldest first
        assert pending[0]["id"] != pending[1]["id"]
        assert store.peek("s1") == pending[0]

        # answering the newer one first must not resolve the older one
        assert store.answer("s1", pending[1]["id"], {"decision": "deny", "reason": "no"}) is True
        assert (await second) == {"decision": "deny", "reason": "no"}
        assert first.done() is False
        assert [p["id"] for p in store.for_session("s1")] == [pending[0]["id"]]

        store.answer("s1", pending[0]["id"], {"decision": "allow"})
        return await first

    assert asyncio.run(run()) == {"decision": "allow"}


def test_one_session_pending_does_not_affect_another():
    store, _ = make_store()

    async def run():
        a = asyncio.create_task(store.request_decision("a", "Bash", {}))
        b = asyncio.create_task(store.request_decision("b", "Edit", {}))
        await asyncio.sleep(0)
        store.answer("a", store.peek("a")["id"], {"decision": "allow"})
        result_a = await a
        assert store.peek("b")["tool_name"] == "Edit"
        store.answer("b", store.peek("b")["id"], {"decision": "deny", "reason": "no"})
        return result_a, await b

    assert asyncio.run(run()) == ({"decision": "allow"}, {"decision": "deny", "reason": "no"})


def test_get_returns_one_prompt_or_none():
    store, _ = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {"command": "ls"}))
        await asyncio.sleep(0)
        prompt_id = store.peek("s1")["id"]
        assert store.get("s1", prompt_id) == {"id": prompt_id, "tool_name": "Bash", "tool_input": {"command": "ls"}}
        assert store.get("s1", "other") is None
        assert store.get("s2", prompt_id) is None
        store.answer("s1", prompt_id, {"decision": "allow"})
        await task

    asyncio.run(run())


# ---------------------------------------------------------------- release with no answer


def test_clear_releases_the_waiter_with_no_answer():
    store, _ = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        assert store.clear("s1", store.peek("s1")["id"]) is True
        return await task

    assert asyncio.run(run()) == {"decision": None}
    assert store.peek("s1") is None


def test_cancelled_waiter_drops_its_prompt():
    store, _ = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run())

    assert store.peek("s1") is None


def test_wait_elapsing_falls_back_to_no_answer():
    store, _ = make_store(max_age=0.05)

    result = asyncio.run(store.request_decision("s1", "Bash", {}))

    assert result == {"decision": None}
    assert store.peek("s1") is None


def test_answer_from_another_thread_wakes_the_waiter():
    store, _ = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        prompt_id = store.peek("s1")["id"]
        worker = threading.Thread(target=store.answer, args=("s1", prompt_id, {"decision": "allow"}))
        worker.start()
        result = await asyncio.wait_for(task, timeout=2)
        worker.join()
        return result

    assert asyncio.run(run()) == {"decision": "allow"}


# ---------------------------------------------------------------- sweep (transcript clearing / max age)


def test_sweep_clears_a_prompt_when_a_later_line_was_written():
    store, clock = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        prompt_id = store.peek("s1")["id"]
        clock.now = 5
        cleared = store.sweep(lambda sid: T0 + timedelta(seconds=3))
        return cleared, prompt_id, await task

    cleared, prompt_id, result = asyncio.run(run())

    assert cleared == [prompt_id]
    assert result == {"decision": None}
    assert store.peek("s1") is None


def test_sweep_keeps_a_prompt_whose_transcript_is_unchanged():
    store, clock = make_store()
    clock.now = 10  # the prompt is registered at T0+10

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        clock.now = 20
        # the newest line predates the prompt, or the transcript is unknown: still pending
        assert store.sweep(lambda sid: T0 + timedelta(seconds=9)) == []
        assert store.sweep(lambda sid: T0 + timedelta(seconds=10)) == []  # written at the same instant
        assert store.sweep(never_active) == []
        assert store.peek("s1") is not None
        store.clear("s1", store.peek("s1")["id"])
        await task

    asyncio.run(run())


def test_sweep_drops_a_prompt_past_the_max_age():
    store, clock = make_store(max_age=100)

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        clock.now = 99
        assert store.sweep(never_active) == []
        clock.now = 100
        cleared = store.sweep(never_active)
        return cleared, await task

    cleared, result = asyncio.run(run())

    assert len(cleared) == 1
    assert result == {"decision": None}
    assert store.peek("s1") is None


def test_sweep_only_clears_the_session_that_moved_on():
    store, clock = make_store()

    async def run():
        a = asyncio.create_task(store.request_decision("a", "Bash", {}))
        b = asyncio.create_task(store.request_decision("b", "Bash", {}))
        await asyncio.sleep(0)
        clock.now = 5
        store.sweep(lambda sid: T0 + timedelta(seconds=3) if sid == "a" else None)
        assert store.peek("a") is None
        assert store.peek("b") is not None
        store.clear("b", store.peek("b")["id"])
        return await a, await b

    assert asyncio.run(run()) == ({"decision": None}, {"decision": None})


def test_sweep_survives_a_failing_lookup():
    store, clock = make_store()

    def boom(sid):
        raise OSError("unreadable transcript")

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        clock.now = 5
        assert store.sweep(boom) == []
        assert store.peek("s1") is not None
        store.clear("s1", store.peek("s1")["id"])
        await task

    asyncio.run(run())


def test_sweep_clears_from_a_worker_thread():
    store, clock = make_store()

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        clock.now = 5
        worker = threading.Thread(target=store.sweep, args=(lambda sid: T0 + timedelta(seconds=3),))
        worker.start()
        result = await asyncio.wait_for(task, timeout=2)
        worker.join()
        return result

    assert asyncio.run(run()) == {"decision": None}


def test_sweep_uses_real_transcript_timestamps(isolated_db, write_transcript):
    """End to end with claude_context.latest_activity over a temporary transcript file."""
    path = claude_context.claude_db.projects_dir() / claude_context.claude_db.sanitize_project_path("/x/proj") / "s1.jsonl"
    stamp = lambda seconds: (T0 + timedelta(seconds=seconds)).isoformat()
    write_transcript(path, [{"type": "user", "timestamp": stamp(1)}, {"type": "assistant", "timestamp": stamp(2)}])
    store, clock = make_store()
    clock.now = 10
    lookup = lambda sid: claude_context.latest_activity(sid, "/x/proj")

    async def run():
        task = asyncio.create_task(store.request_decision("s1", "Bash", {}))
        await asyncio.sleep(0)
        assert store.sweep(lookup) == []  # nothing written since the prompt appeared

        clock.now = 15
        write_transcript(
            path,
            [
                {"type": "user", "timestamp": stamp(1)},
                {"type": "assistant", "timestamp": stamp(2)},
                {"type": "user", "timestamp": stamp(12)},  # the tool result, after the prompt at +10
            ],
        )
        assert len(store.sweep(lookup)) == 1
        return await task

    assert asyncio.run(run()) == {"decision": None}


# ---------------------------------------------------------------- Remote mode


def test_remote_mode_starts_off():
    store, _ = make_store()

    assert store.remote_mode() == {"enabled": False, "expires_at": None}
    assert store.remote_mode_enabled() is False


def test_remote_mode_can_be_switched_on_and_off():
    store, clock = make_store()

    store.set_remote_mode(True)
    assert store.remote_mode_enabled() is True
    assert store.remote_mode() == {
        "enabled": True,
        "expires_at": (T0 + timedelta(hours=8)).isoformat(),
    }

    store.set_remote_mode(False)
    assert store.remote_mode() == {"enabled": False, "expires_at": None}


def test_remote_mode_expires_after_eight_hours():
    store, clock = make_store()
    store.set_remote_mode(True)

    clock.now = 8 * 3600 - 1
    assert store.remote_mode_enabled() is True

    clock.now = 8 * 3600
    assert store.remote_mode_enabled() is False
    assert store.remote_mode() == {"enabled": False, "expires_at": None}


def test_re_enabling_remote_mode_restarts_the_window():
    store, clock = make_store()
    store.set_remote_mode(True)
    clock.now = 7 * 3600
    store.set_remote_mode(True)

    clock.now = 9 * 3600  # past the first window, inside the second
    assert store.remote_mode_enabled() is True


def test_a_new_store_starts_off_like_a_restart():
    first, _ = make_store()
    first.set_remote_mode(True)

    assert make_store()[0].remote_mode_enabled() is False
