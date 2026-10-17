"""The full per-session detail: turns, attribution and breakdown, parsed from the transcript."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

from app.domain.context import breakdown, tail
from app.domain.context.attribution import attribute_growth, is_cache_miss
from app.domain.context.models import Breakdown, Compaction, SessionDetail, StartupEvent, Turn
from app.domain.context.parsing import scan

log = logging.getLogger("ledger")


def _safe_breakdown(
    turns: list[Turn], compactions: list[Compaction], events: list[StartupEvent], session_id: str
) -> Optional[Breakdown]:
    """The breakdown, or None (logged) if it cannot be built, so a bad attachment never costs the detail view."""
    try:
        return breakdown.build_breakdown(turns, compactions, events)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        log.warning("context breakdown failed session_id=%s", session_id, exc_info=True)
        return None


def parse_detail(lines: Iterable[str], session_id: str = "") -> SessionDetail:
    turns, compactions, events = scan(lines)
    for index, turn in enumerate(turns):
        turn.cache_miss = is_cache_miss(index, turn)
    return SessionDetail(
        turns=turns,
        compactions=compactions,
        attribution=attribute_growth(turns, compactions),
        breakdown=_safe_breakdown(turns, compactions, events, session_id),
    )


# path -> (stat key at last parse, detail)
_detail_cache: dict[Path, tuple[tuple[int, int], SessionDetail]] = {}


def load_detail(session_id: str, cwd: str) -> Optional[SessionDetail]:
    """Full parse of a session's transcript for the detail view (memoized by file stat), or None. Never raises."""
    try:
        path = tail.transcript_path(session_id, cwd)
        if path is None:
            return None
        key = tail.stat_key(path)
        cached = _detail_cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]

        with path.open("r", encoding="utf-8", errors="replace") as f:
            detail = parse_detail(f, session_id)
        _detail_cache[path] = (key, detail)
        return detail
    except (OSError, ValueError):
        return None
