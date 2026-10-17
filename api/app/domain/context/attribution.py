"""Attributing context growth to the tool calls that caused it."""

from __future__ import annotations


from app.domain.context.models import Attribution, Compaction, Increase, ToolGrowth, ToolUse, Turn


_NO_TOOL_LABEL = "prompt / text"
_TOP_INCREASES = 5


def is_cache_miss(index: int, turn: Turn) -> bool:
    """A response other than the first that wrote more cache than it read (a fresh session's first one always does)."""
    return index > 0 and turn.cache_written > turn.cache_read


def credited_tool(previous: Turn) -> ToolUse:
    """The tool credited with the context growth that arrives at the response after `previous`."""
    return previous.tools[0] if previous.tools else ToolUse(_NO_TOOL_LABEL)


def attribute_growth(turns: list[Turn], compactions: list[Compaction]) -> Attribution:
    """Attribute context growth since the last compaction to the tool whose result caused it.

    The context delta arriving at response t is what the previous response's tool call brought back,
    so it goes to that response's first tool (or to "prompt / text" when it called none). Deltas are
    signed so that `floor + sum(all attributed) == current` holds exactly even if the context shrank
    partway through a segment without a recorded compaction.
    """
    start = compactions[-1].position if compactions else 0
    segment = turns[start:]
    if not segment:
        return Attribution(floor=0, current=0, by_tool=[], largest=[])

    totals: dict[str, list[int]] = {}
    increases: list[Increase] = []
    for offset in range(1, len(segment)):
        previous = segment[offset - 1]
        tool = credited_tool(previous)
        delta = segment[offset].context - previous.context
        entry = totals.setdefault(tool.name, [0, 0])
        entry[0] += delta
        entry[1] += 1
        if delta > 0:
            increases.append(Increase(index=start + offset, tokens=delta, tool=tool.name, hint=tool.hint))

    by_tool = sorted((ToolGrowth(name, tokens, uses) for name, (tokens, uses) in totals.items()), key=lambda g: -g.tokens)
    increases.sort(key=lambda inc: -inc.tokens)  # stable: ties keep chronological order
    return Attribution(floor=segment[0].context, current=segment[-1].context, by_tool=by_tool, largest=increases[:_TOP_INCREASES])
