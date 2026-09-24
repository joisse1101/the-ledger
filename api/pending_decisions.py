"""In-memory store for live sessions' pending tool-permission decisions.

Ephemeral and lock-guarded, mirroring live_snapshot.py's pattern - nothing here touches disk. A
session counts as "watched" only while a browser is actively polling its pending-decision endpoint
(touch_watch is that poll's side effect); request_decision() uses that to decide whether a
PreToolUse call is worth registering and blocking for at all, per design.md's "is anyone watching"
gate - an unwatched session gets an immediate "no opinion" so it behaves exactly as it does without
the relay hook.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

WATCH_WINDOW_SECONDS = 5.0
DECISION_WAIT_SECONDS = 120.0

NO_OPINION: dict[str, Any] = {"decision": None, "reason": None}


@dataclass
class _Pending:
    tool_name: str
    tool_input: dict
    created_at: float
    event: asyncio.Event = field(default_factory=asyncio.Event)
    answer: Optional[dict[str, Any]] = None


class PendingDecisions:
    def __init__(
        self,
        watch_window: float = WATCH_WINDOW_SECONDS,
        wait_timeout: float = DECISION_WAIT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._watch_window = watch_window
        self._wait_timeout = wait_timeout
        self._clock = clock
        self._lock = threading.Lock()
        self._last_watched: dict[str, float] = {}
        self._pending: dict[str, _Pending] = {}

    def touch_watch(self, session_id: str) -> None:
        """Called as a side effect of polling a session's pending-decision endpoint."""
        with self._lock:
            self._last_watched[session_id] = self._clock()

    def is_watched(self, session_id: str) -> bool:
        with self._lock:
            last = self._last_watched.get(session_id)
        return last is not None and self._clock() - last < self._watch_window

    def peek(self, session_id: str) -> Optional[dict[str, Any]]:
        """The pending decision's tool name/input, if any - for the poll response and /api/live."""
        with self._lock:
            pending = self._pending.get(session_id)
            if pending is None:
                return None
            return {"tool_name": pending.tool_name, "tool_input": pending.tool_input}

    def answer(self, session_id: str, decision: str, reason: Optional[str] = None) -> bool:
        """Called when the browser answers a pending decision. False means nothing was pending
        (already answered or timed out) - the caller should treat that as a 409."""
        with self._lock:
            pending = self._pending.get(session_id)
            if pending is None:
                return False
            pending.answer = {"decision": decision, "reason": reason}
        pending.event.set()
        return True

    async def request_decision(self, session_id: str, tool_name: str, tool_input: dict) -> dict[str, Any]:
        """Called by the relay hook. Returns "no opinion" immediately unless the session is
        currently watched, in which case it registers the decision and waits up to the configured
        timeout for an answer, falling back to "no opinion" either way once it elapses."""
        if not self.is_watched(session_id):
            return dict(NO_OPINION)

        pending = _Pending(tool_name=tool_name, tool_input=tool_input, created_at=self._clock())
        with self._lock:
            self._pending[session_id] = pending

        try:
            await asyncio.wait_for(pending.event.wait(), timeout=self._wait_timeout)
        except asyncio.TimeoutError:
            pass

        with self._lock:
            if self._pending.get(session_id) is pending:
                del self._pending[session_id]

        return pending.answer or dict(NO_OPINION)
