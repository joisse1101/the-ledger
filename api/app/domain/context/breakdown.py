"""Estimating what the startup content adds to the context window."""

from __future__ import annotations

from bisect import bisect_right

from app.domain.context.attribution import credited_tool
from app.domain.context.models import Breakdown, Compaction, GrowthRow, RawItem, StartupCategory, StartupEvent, StartupItem, StartupSnapshot, Turn, TurnBreakdown


_CHARS_PER_TOKEN = 4  # the rough estimate for startup content; the transcript has no tokenizer to use


_CATEGORY_NAMES = (("memory", "Memory files"), ("skills", "Skills"), ("agents", "Custom agents"), ("mcp", "MCP instructions"))


def estimate_tokens(text: str) -> int:
    return -(-len(text) // _CHARS_PER_TOKEN)  # ceiling division


def _apply_event(state: dict[str, dict[str, RawItem]], event: StartupEvent) -> None:
    items = state.setdefault(event.category, {})
    if event.replace:
        items.clear()
    for item in event.added:
        items[item.key] = item
    for key in event.removed:
        items.pop(key, None)


def _categories(state: dict[str, dict[str, RawItem]], floor: int) -> list[StartupCategory]:
    """The state's categories with `chars/4` estimates, scaled down (never up) so they total at most `floor`."""
    estimated = [
        (name, sorted(((item.label, estimate_tokens(item.text)) for item in state[key].values()), key=lambda i: -i[1]))
        for key, name in _CATEGORY_NAMES
        if state.get(key)
    ]
    total = sum(tokens for _, items in estimated for _, tokens in items)
    categories = []
    for name, items in estimated:
        # Integer arithmetic keeps the floor exact: the sum of floored shares can never exceed `floor`.
        scaled = [StartupItem(label, tokens * floor // total if total > floor else tokens) for label, tokens in items]
        categories.append(StartupCategory(name, sum(item.tokens for item in scaled), scaled))
    return categories


def build_breakdown(turns: list[Turn], compactions: list[Compaction], events: list[StartupEvent]) -> Breakdown:
    """Split every response's context into estimated startup categories, exact growth by tool, and a remainder.

    A segment starts at the first response and at the first response after each compaction. Growth is
    cumulative within a segment and credited by `credited_tool`. Startup estimates are capped at the
    segment's first response, so the remainder (`floor - startup`) is never negative and every row set
    sums to its response's exact context.
    """
    if not turns:
        return Breakdown(snapshots=[], turns=[])

    segment_starts = sorted({0, *(c.position for c in compactions if 0 < c.position < len(turns))})
    positions = sorted({*segment_starts, *(e.position for e in events if e.position < len(turns))})
    pending = sorted(events, key=lambda e: e.position)  # stable: events at one position keep their order

    state: dict[str, dict[str, RawItem]] = {}
    snapshots: list[StartupSnapshot] = []
    applied = 0
    for position in positions:
        while applied < len(pending) and pending[applied].position <= position:
            _apply_event(state, pending[applied])
            applied += 1
        floor = turns[segment_starts[bisect_right(segment_starts, position) - 1]].context
        categories = _categories(state, floor)
        if not snapshots or snapshots[-1].categories != categories:
            snapshots.append(StartupSnapshot(position, categories))

    segment_set = set(segment_starts)
    snapshot_positions = [snapshot.position for snapshot in snapshots]
    rows: list[TurnBreakdown] = []
    cumulative: dict[str, int] = {}
    for index, turn in enumerate(turns):
        if index in segment_set:
            cumulative = {}
        else:
            previous = turns[index - 1]
            tool = credited_tool(previous).name
            cumulative[tool] = cumulative.get(tool, 0) + turn.context - previous.context
        snapshot = bisect_right(snapshot_positions, index) - 1
        startup = sum(category.tokens for category in snapshots[snapshot].categories)
        growth = sorted(((tool, tokens) for tool, tokens in cumulative.items() if tokens), key=lambda g: -g[1])
        remainder = turn.context - startup - sum(tokens for _, tokens in growth)
        rows.append(TurnBreakdown(snapshot, [GrowthRow(tool, tokens) for tool, tokens in growth], remainder))
    return Breakdown(snapshots=snapshots, turns=rows)
