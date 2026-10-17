"""The snapshot rescan: serialised under one lock, and repeated on a timer while the server is up."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime

from app.repositories import claude_db

log = logging.getLogger("ledger")

# The background rescan runs every 10 minutes for as long as the server is up.
REFRESH_INTERVAL_SECONDS = 10 * 60

# refresh() rewrites both tables and can take seconds on a big history, so it is
# serialised process-wide: startup, the timer and POST /api/refresh never overlap. Routes that
# delete rows take it too, so a concurrent rescan can't re-add them.
lock = threading.Lock()


def locked_refresh() -> datetime:
    with lock:
        return claude_db.refresh()


def startup_snapshot() -> None:
    with lock:
        claude_db.startup()


async def refresh_loop(interval: float = REFRESH_INTERVAL_SECONDS) -> None:
    """Rescan every `interval` seconds, in a worker thread, until cancelled."""
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(locked_refresh)
        except Exception:
            # A bad scan must not end the loop; the next tick tries again.
            log.exception("background refresh failed")
