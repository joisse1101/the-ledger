"""In-memory store for live sessions' pending prompts, plus the Remote mode switch.

Ephemeral and lock-guarded, mirroring live_snapshot.py's pattern - nothing here touches disk. The
relay hook (a PermissionRequest hook) registers every prompt its session is about to show, then waits
on it; whichever surface answers first wins. A dashboard answer resolves the waiting hook request. A
terminal answer is never heard directly, so sweep() notices it from the session's transcript (a line
written after the prompt was registered) and releases the hook with no answer. A maximum age is the
backstop for anything else. Remote mode is only state here - the routes apply it as an access gate.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

PROMPT_MAX_AGE_SECONDS = 30 * 60.0
REMOTE_MODE_TTL_SECONDS = 8 * 60 * 60.0


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class _Prompt:
    id: str
    session_id: str
    tool_name: str
    tool_input: dict
    created_at: float  # the store's monotonic clock: for the max-age backstop
    created_wall: datetime  # compared against transcript line timestamps
    loop: Optional[asyncio.AbstractEventLoop]
    event: asyncio.Event = field(default_factory=asyncio.Event)
    answer: Optional[dict[str, Any]] = None


class PendingDecisions:
    def __init__(
        self,
        max_age: float = PROMPT_MAX_AGE_SECONDS,
        remote_mode_ttl: float = REMOTE_MODE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._max_age = max_age
        self._remote_mode_ttl = remote_mode_ttl
        self._clock = clock
        self._wall_clock = wall_clock
        self._lock = threading.Lock()
        self._prompts: dict[str, list[_Prompt]] = {}
        self._remote_expires: Optional[float] = None  # None = off
        self._remote_expires_at: Optional[datetime] = None

    # ------------------------------------------------------------ Remote mode

    def _remote_enabled(self) -> bool:
        """Whether Remote mode is on right now, switching it off if it has expired. Caller holds the lock."""
        if self._remote_expires is not None and self._clock() >= self._remote_expires:
            self._remote_expires = None
            self._remote_expires_at = None
        return self._remote_expires is not None

    def set_remote_mode(self, enabled: bool) -> None:
        with self._lock:
            if enabled:
                self._remote_expires = self._clock() + self._remote_mode_ttl
                self._remote_expires_at = self._wall_clock() + timedelta(seconds=self._remote_mode_ttl)
            else:
                self._remote_expires = None
                self._remote_expires_at = None

    def remote_mode(self) -> dict[str, Any]:
        """`{enabled, expires_at}` for the API; expires_at is an ISO timestamp, None when off."""
        with self._lock:
            enabled = self._remote_enabled()
            return {"enabled": enabled, "expires_at": self._remote_expires_at.isoformat() if enabled else None}

    def remote_mode_enabled(self) -> bool:
        with self._lock:
            return self._remote_enabled()

    # ------------------------------------------------------------ prompts

    def register(self, session_id: str, tool_name: str, tool_input: dict) -> str:
        """Store a new pending prompt for the session and return its API-generated id.

        Call from the event loop that will wait on it (request_decision does), so a release from
        another thread can wake it safely.
        """
        try:
            loop: Optional[asyncio.AbstractEventLoop] = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        prompt = _Prompt(
            id=uuid.uuid4().hex,
            session_id=session_id,
            tool_name=tool_name,
            tool_input=tool_input,
            created_at=self._clock(),
            created_wall=self._wall_clock(),
            loop=loop,
        )
        with self._lock:
            self._prompts.setdefault(session_id, []).append(prompt)
        return prompt.id

    def _find(self, session_id: str, prompt_id: str) -> Optional[_Prompt]:
        return next((p for p in self._prompts.get(session_id, []) if p.id == prompt_id), None)

    def _remove(self, prompt: _Prompt) -> None:
        """Drop the prompt from its session's list. Caller holds the lock."""
        remaining = [p for p in self._prompts.get(prompt.session_id, []) if p is not prompt]
        if remaining:
            self._prompts[prompt.session_id] = remaining
        else:
            self._prompts.pop(prompt.session_id, None)

    @staticmethod
    def _release(prompt: _Prompt) -> None:
        """Wake whoever is waiting on the prompt, from whichever thread this runs on.

        asyncio.Event isn't safe to set() from another thread (a plain `def` route runs in
        Starlette's threadpool), so hop onto the waiter's own loop when there is one.
        """
        if prompt.loop is None:
            prompt.event.set()
            return
        try:
            prompt.loop.call_soon_threadsafe(prompt.event.set)
        except RuntimeError:  # the loop is already closed: nobody is left waiting
            pass

    def for_session(self, session_id: str) -> list[dict[str, Any]]:
        """The session's pending prompts, oldest first."""
        with self._lock:
            return [
                {"id": p.id, "tool_name": p.tool_name, "tool_input": p.tool_input}
                for p in self._prompts.get(session_id, [])
            ]

    def peek(self, session_id: str) -> Optional[dict[str, Any]]:
        """The session's oldest pending prompt, if any - for /api/live's `pending_decision`."""
        prompts = self.for_session(session_id)
        return prompts[0] if prompts else None

    def get(self, session_id: str, prompt_id: str) -> Optional[dict[str, Any]]:
        """One pending prompt, for validating an answer against it."""
        with self._lock:
            prompt = self._find(session_id, prompt_id)
            if prompt is None:
                return None
            return {"id": prompt.id, "tool_name": prompt.tool_name, "tool_input": prompt.tool_input}

    def answer(self, session_id: str, prompt_id: str, answer: dict[str, Any]) -> bool:
        """Resolve the prompt with `answer`. False means it is gone (answered, cleared or expired) -
        the caller should treat that as a 409."""
        with self._lock:
            prompt = self._find(session_id, prompt_id)
            if prompt is None:
                return False
            prompt.answer = answer
            self._remove(prompt)
        self._release(prompt)
        return True

    def clear(self, session_id: str, prompt_id: str) -> bool:
        """Drop the prompt without an answer, releasing its waiter with "no answer"."""
        with self._lock:
            prompt = self._find(session_id, prompt_id)
            if prompt is None:
                return False
            self._remove(prompt)
        self._release(prompt)
        return True

    def sweep(self, latest_activity: Callable[[str], Optional[datetime]]) -> list[str]:
        """Clear every prompt whose session has moved on, or that outlived the maximum age.

        `latest_activity(session_id)` is the timestamp of the newest `user` line in that session's
        transcript (None when unknown). Such a line stamped after the prompt was registered is the
        tool result, i.e. the prompt was answered somewhere else. Returns the cleared prompt ids.
        """
        now = self._clock()
        with self._lock:
            candidates = [p for prompts in self._prompts.values() for p in prompts]

        cleared: list[_Prompt] = []
        for prompt in candidates:
            if now - prompt.created_at >= self._max_age:
                cleared.append(prompt)
                continue
            try:
                latest = latest_activity(prompt.session_id)
            except Exception:  # one unreadable transcript must not stop the rest
                continue
            if latest is not None and latest > prompt.created_wall:
                cleared.append(prompt)

        released: list[str] = []
        for prompt in cleared:
            with self._lock:
                if self._find(prompt.session_id, prompt.id) is None:
                    continue  # answered while we were reading transcripts
                self._remove(prompt)
            self._release(prompt)
            released.append(prompt.id)
        return released

    async def request_decision(self, session_id: str, tool_name: str, tool_input: dict) -> dict[str, Any]:
        """Called by the relay hook's request: register the prompt and wait for its answer.

        Returns the answer (`{decision: "allow"}`, `{decision: "deny", reason}` or `{decision:
        "answer", answers}`), or `{decision: None}` when it was cleared, timed out or the hook's
        connection dropped - the hook then prints nothing and the terminal dialog stays the only way.
        """
        prompt_id = self.register(session_id, tool_name, tool_input)
        with self._lock:
            prompt = self._find(session_id, prompt_id)
        assert prompt is not None

        try:
            await asyncio.wait_for(prompt.event.wait(), timeout=self._max_age)
        except asyncio.TimeoutError:
            pass
        finally:
            with self._lock:
                if self._find(session_id, prompt_id) is not None:
                    self._remove(prompt)

        return prompt.answer or {"decision": None}
