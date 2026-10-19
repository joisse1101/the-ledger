"""Grading a live session by the time since it started or was last compacted.

Pure: no I/O and no clock of its own, so the bands are tested with explicit datetimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

SHOULD_COMPACT_AFTER = timedelta(minutes=45)
NEEDS_COMPACT_AFTER = timedelta(minutes=55)


@dataclass(frozen=True)
class CompactGrade:
    state: str  # "ok" | "should" | "needs"
    since: datetime  # timezone-aware UTC: the later of the session's start and its last compaction


def _utc(value: datetime) -> datetime:
    """Naive datetimes are local time (the session registry's); aware ones are converted."""
    return value.astimezone(timezone.utc)


def grade_compact(
    started_at: Optional[datetime], last_compaction: Optional[datetime], now: datetime
) -> Optional[CompactGrade]:
    """The session's grade, or None when neither a start nor a compaction time is known."""
    anchors = [_utc(value) for value in (started_at, last_compaction) if value is not None]
    if not anchors:
        return None
    since = max(anchors)
    elapsed = _utc(now) - since
    if elapsed > NEEDS_COMPACT_AFTER:
        state = "needs"
    elif elapsed >= SHOULD_COMPACT_AFTER:
        state = "should"
    else:
        state = "ok"
    return CompactGrade(state=state, since=since)
