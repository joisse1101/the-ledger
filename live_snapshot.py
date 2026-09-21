"""Coalesced, thread-safe view of the live session registry for the API.

Every connected browser polls /api/live every ~2s. `claude_sessions` and
`claude_context` keep module-level caches written for a single script thread, so
all reads of them go through one lock, and a result younger than the TTL is
served as is - N devices cost about one recompute per TTL, not N.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

import claude_context
import claude_sessions

LIVE_TTL_SECONDS = 1.0


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


class LiveSnapshot:
    def __init__(
        self,
        load_sessions: Optional[Callable[[], list]] = None,
        live_context: Optional[Callable[[str, str], Any]] = None,
        ttl: float = LIVE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        # Resolved late so tests (and callers) can patch the underlying modules.
        self._load_sessions = load_sessions or (lambda: claude_sessions.load_sessions())
        self._live_context = live_context or (
            lambda session_id, cwd: claude_context.live_context(session_id, cwd)
        )
        self._ttl = ttl
        self._clock = clock
        self._lock = threading.Lock()
        self._computed_at: Optional[float] = None
        self._items: list[dict[str, Any]] = []
        self._cwds: dict[str, str] = {}

    def _ensure_fresh(self) -> None:
        """Recompute if the last result is older than the TTL. The caller holds the lock."""
        now = self._clock()
        if self._computed_at is None or now - self._computed_at >= self._ttl:
            sessions = self._load_sessions()
            self._items = [self._item(s) for s in sessions]
            self._cwds = {s.session_id: s.cwd for s in sessions}
            self._computed_at = now

    def get(self) -> list[dict[str, Any]]:
        """The live sessions, newest-updated first, each with its `context` (or None)."""
        with self._lock:
            self._ensure_fresh()
            return self._items

    def live_ids(self) -> set[str]:
        return {item["session_id"] for item in self.get()}

    def cwd_for(self, session_id: str) -> Optional[str]:
        """The registry's working directory for a live session, or None. Never sent to clients."""
        with self._lock:
            self._ensure_fresh()
            return self._cwds.get(session_id)

    def is_live_now(self, session_id: str) -> bool:
        """Whether the session is registered right now: a fresh read, never the cached result."""
        with self._lock:
            return any(s.session_id == session_id for s in self._load_sessions())

    def _context(self, session) -> Optional[dict[str, Any]]:
        # One unreadable transcript must not sink the whole list.
        try:
            context = self._live_context(session.session_id, session.cwd)
        except Exception:
            return None
        if not context:
            return None
        return {
            "size": context.size,
            "growth": context.growth,
            "history": list(context.history),
            "label": claude_context.format_context(context),
        }

    def _item(self, s) -> dict[str, Any]:
        return {
            "session_id": s.session_id,
            "pid": s.pid,
            "name": s.name,
            "project": s.project,
            "title": s.title,
            "status": s.status,
            "kind": s.kind,
            "started_at": _iso(s.started_at),
            "updated_at": _iso(s.updated_at),
            "last_message": s.last_message,
            "first_prompt": s.first_prompt,
            "context": self._context(s),
        }
