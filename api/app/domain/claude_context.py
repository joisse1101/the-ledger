"""Live context size and per-session token history, read straight from a session's transcript.

Like `claude_sessions.py`, this deliberately bypasses the SQLite snapshot in `app/repositories/db/`: the
Live table polls every 2s, and a snapshot that only refreshes on demand would leave the gauge stale
(and blank for brand-new sessions). Everything here is absolute tokens - the transcript doesn't say
what a model's context window is, so nothing is expressed as a percentage of a limit.
"""

from __future__ import annotations

import json
import logging
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from app.repositories.db import paths, scanner

log = logging.getLogger("ledger")

SPARKLINE_TURNS = 24
_CHARS_PER_TOKEN = 4  # the rough estimate for startup content; the transcript has no tokenizer to use
_TAIL_WINDOW = 256 * 1024
_SPARK_GLYPHS = "▁▂▃▄▅▆▇█"
_NO_TOOL_LABEL = "prompt / text"
_TOP_INCREASES = 5
_HINT_KEYS = ("file_path", "path", "command", "pattern", "url", "query", "description", "prompt")
_HINT_MAX_CHARS = 80


@dataclass(frozen=True)
class ToolUse:
    name: str
    hint: str = ""


@dataclass
class Turn:
    """One real main-thread response from Claude, as the API reported its token usage."""

    message_id: str
    timestamp: Optional[datetime]
    new: int
    cache_read: int
    cache_written: int
    output: int
    tools: list[ToolUse] = field(default_factory=list)
    cache_miss: bool = False

    @property
    def context(self) -> int:
        return self.new + self.cache_read + self.cache_written


@dataclass(frozen=True)
class Compaction:
    position: int  # number of real turns that precede it
    trigger: str = ""
    pre_tokens: Optional[int] = None


@dataclass(frozen=True)
class LiveContext:
    size: int
    growth: Optional[int]  # None until a second response exists
    history: list[int]  # context of up to the SPARKLINE_TURNS most recent responses, oldest first


@dataclass(frozen=True)
class ToolGrowth:
    tool: str
    tokens: int
    uses: int


@dataclass(frozen=True)
class Increase:
    index: int  # index into SessionDetail.turns of the response whose context grew
    tokens: int
    tool: str
    hint: str


@dataclass(frozen=True)
class Attribution:
    floor: int  # context of the first response in the segment (nothing is attributed to it)
    current: int
    by_tool: list[ToolGrowth]
    largest: list[Increase]


@dataclass(frozen=True)
class StartupItem:
    label: str
    tokens: int


@dataclass(frozen=True)
class StartupCategory:
    name: str
    tokens: int  # always the sum of its items
    items: list[StartupItem]


@dataclass(frozen=True)
class StartupSnapshot:
    """The estimated startup content from `position` (a response index) until the next snapshot."""

    position: int
    categories: list[StartupCategory]


@dataclass(frozen=True)
class GrowthRow:
    tool: str
    tokens: int  # exact, cumulative since the start of the segment


@dataclass(frozen=True)
class TurnBreakdown:
    snapshot: int  # index into Breakdown.snapshots
    growth: list[GrowthRow]
    remainder: int  # context minus every other row, so the rows always sum to the response's context


@dataclass(frozen=True)
class Breakdown:
    snapshots: list[StartupSnapshot]
    turns: list[TurnBreakdown]  # one per SessionDetail.turns entry


@dataclass(frozen=True)
class SessionDetail:
    turns: list[Turn]
    compactions: list[Compaction]
    attribution: Attribution
    breakdown: Optional[Breakdown] = None  # None when it could not be built


# ---------------------------------------------------------------- startup content events


@dataclass(frozen=True)
class RawItem:
    key: str  # identity within a category: a file path, a skill, agent or server name
    label: str
    text: str


@dataclass(frozen=True)
class StartupEvent:
    """Startup content Claude Code recorded just before response number `position` (0-based)."""

    position: int
    category: str  # memory | skills | agents | mcp
    added: tuple[RawItem, ...]
    removed: tuple[str, ...] = ()
    replace: bool = False  # an initial listing: forget what the category held before


def _str_list(value: Any) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _listing_items(text: str) -> tuple[RawItem, ...]:
    """Group `- name: description` lines into items; a line not starting with `- ` continues the previous one."""
    groups: list[list[str]] = []
    for line in text.split("\n"):
        if line.startswith("- ") or not groups:
            groups.append([line])
        else:
            groups[-1].append(line)
    items = []
    for group in groups:
        body = "\n".join(group)
        name = (body[2:] if body.startswith("- ") else body).split(":", 1)[0].strip()
        if name:
            items.append(RawItem(key=name, label=name, text=body))
    return tuple(items)


def _memory_items(files: Any) -> tuple[RawItem, ...]:
    items = []
    for file in files if isinstance(files, list) else []:
        if not isinstance(file, dict) or not isinstance(file.get("path"), str) or not isinstance(file.get("content"), str):
            continue
        path = file["path"]
        items.append(RawItem(key=path, label="/".join(re.split(r"[\\/]", path)[-2:]), text=file["content"]))
    return tuple(items)


def _mcp_items(attachment: dict) -> tuple[RawItem, ...]:
    blocks, names = _str_list(attachment.get("addedBlocks")), _str_list(attachment.get("addedNames"))
    items = []
    for index, block in enumerate(blocks):
        name = names[index] if len(names) == len(blocks) else block.split("\n", 1)[0].removeprefix("## ").strip()
        if name:
            items.append(RawItem(key=name, label=name, text=block))
    return tuple(items)


def _startup_events(attachment: Any, position: int) -> list[StartupEvent]:
    """The startup-content events carried by one transcript attachment, or [] for any other or malformed one."""
    if not isinstance(attachment, dict):
        return []
    kind = attachment.get("type")
    initial = attachment.get("isInitial") is True
    if kind == "instructions":
        event = StartupEvent(position, "memory", _memory_items(attachment.get("files")))
    elif kind == "skill_listing" and isinstance(attachment.get("content"), str):
        event = StartupEvent(position, "skills", _listing_items(attachment["content"]), replace=initial)
    elif kind == "agent_listing_delta":
        added = _listing_items("\n".join(_str_list(attachment.get("addedLines"))))
        event = StartupEvent(position, "agents", added, tuple(_str_list(attachment.get("removedTypes"))), replace=initial)
    elif kind == "mcp_instructions_delta":
        event = StartupEvent(position, "mcp", _mcp_items(attachment), tuple(_str_list(attachment.get("removedNames"))))
    else:
        return []
    return [event] if event.added or event.removed or event.replace else []


# ---------------------------------------------------------------- parsing


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _tool_hint(tool_input: Any) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in _HINT_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            hint = " ".join(value.split())
            return hint if len(hint) <= _HINT_MAX_CHARS else hint[: _HINT_MAX_CHARS - 1] + "…"
    return ""


def _tool_uses(content: Any) -> list[ToolUse]:
    if not isinstance(content, list):
        return []
    return [
        ToolUse(name=block["name"], hint=_tool_hint(block.get("input")))
        for block in content
        if isinstance(block, dict) and block.get("type") == "tool_use" and isinstance(block.get("name"), str)
    ]


def _scan(lines: Iterable[str]) -> tuple[list[Turn], list[Compaction], list[StartupEvent]]:
    turns: dict[str, Turn] = {}
    compactions: list[Compaction] = []
    events: list[StartupEvent] = []

    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue

        if entry.get("type") == "attachment":
            if not entry.get("isSidechain"):
                events.extend(_startup_events(entry.get("attachment"), len(turns)))
            continue

        if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
            meta = entry.get("compactMetadata")
            meta = meta if isinstance(meta, dict) else {}
            pre_tokens = meta.get("preTokens")
            trigger = (meta.get("trigger") if isinstance(meta, dict) else None) or ""
            compactions.append(
                Compaction(
                    position=len(turns),
                    trigger=trigger,
                    pre_tokens=pre_tokens if isinstance(pre_tokens, int) else None,
                )
            )
            continue

        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or message.get("model") == "<synthetic>":
            continue
        usage, message_id = message.get("usage"), message.get("id")
        if not isinstance(usage, dict) or not isinstance(message_id, str):
            continue

        turn = Turn(
            message_id=message_id,
            timestamp=scanner.parse_iso_timestamp(entry.get("timestamp")),
            new=_int(usage.get("input_tokens")),
            cache_read=_int(usage.get("cache_read_input_tokens")),
            cache_written=_int(usage.get("cache_creation_input_tokens")),
            output=_int(usage.get("output_tokens")),
        )
        if turn.context == 0:
            continue

        # A multi-block turn spans several lines that repeat the same id and usage, but each line
        # carries different content blocks - the last line's usage wins, the tools accumulate.
        previous = turns.get(message_id)
        turn.tools = (previous.tools if previous else []) + _tool_uses(message.get("content"))
        turns[message_id] = turn

    return list(turns.values()), compactions, events


def extract_turns(lines: Iterable[str]) -> list[Turn]:
    """Real main-thread responses in order: no sidechains, no `<synthetic>`/zero-usage placeholders."""
    return _scan(lines)[0]


# ---------------------------------------------------------------- formatting


def _thousands(n: int) -> int:
    return (n + 500) // 1000  # half-up; Python's round() is banker's


def humanise_tokens(n: int) -> str:
    """742 -> `742`, 80,618 -> `81k`, 1,234,567 -> `1.2M`.

    Keep in step with the toast hook's Format-TokenCount and web's humanizeTokens.
    """
    if n < 1000:
        return str(n)
    if _thousands(n) < 1000:
        return f"{_thousands(n)}k"
    return f"{n / 1_000_000:.1f}M"


def _humanise_delta(n: int) -> str:
    """Like `humanise_tokens`, but keeps one decimal in the k range: growth is small (`2.1k`)."""
    if n < 1000:
        return str(n)
    if round(n / 1000, 1) < 1000:
        return f"{n / 1000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def format_growth(delta: int) -> str:
    if delta == 0:
        return "• 0"
    marker, sign = ("▲", "+") if delta > 0 else ("▼", "-")
    return f"{marker} {sign}{_humanise_delta(abs(delta))}"


def sparkline(values: list[int]) -> str:
    """Block-glyph trend scaled from zero (not the window minimum) to the window maximum."""
    peak = max(values, default=0)
    if peak <= 0:
        return ""
    top = len(_SPARK_GLYPHS) - 1
    return "".join(_SPARK_GLYPHS[min(top, max(0, int(v / peak * len(_SPARK_GLYPHS))))] for v in values)


def format_context(context: LiveContext) -> str:
    """The Live table's Context cell: `394k ▲ +2.1k ▁▂▂▃▅▆▇`, or just the size for a single response."""
    parts = [humanise_tokens(context.size)]
    if context.growth is not None:
        parts.append(format_growth(context.growth))
        parts.append(sparkline(context.history))
    return " ".join(parts)


# ---------------------------------------------------------------- live tail-read


def _read_tail_turns(path: Path, limit: int = SPARKLINE_TURNS) -> list[Turn]:
    """The last `limit` real turns, reading backwards from EOF in a window that doubles until enough are found."""
    window = _TAIL_WINDOW
    with path.open("rb") as f:
        size = f.seek(0, os.SEEK_END)
        while True:
            start = max(0, size - window)
            f.seek(start)
            lines = f.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]  # the window probably began mid-record
            turns = extract_turns(line.decode("utf-8", errors="replace") for line in lines)
            if len(turns) >= limit or start == 0:
                return turns[-limit:]
            window *= 2


# session id -> transcript found by glob rather than by its sanitized cwd
_located: dict[str, Path] = {}


def transcript_path(session_id: str, cwd: str) -> Optional[Path]:
    root = paths.projects_dir()
    direct = root / paths.sanitize_project_path(cwd) / f"{session_id}.jsonl"
    if direct.is_file():
        return direct

    remembered = _located.get(session_id)
    if remembered is not None and remembered.is_file():
        return remembered

    found = next(root.glob(f"*/{session_id}.jsonl"), None)
    if found is not None:
        _located[session_id] = found
    return found


def _stat_key(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


# path -> (stat key at last read, result)
_live_cache: dict[Path, tuple[tuple[int, int], Optional[LiveContext]]] = {}


def live_context(session_id: str, cwd: str) -> Optional[LiveContext]:
    """The session's current context size, growth and recent history, or None when unavailable. Never raises."""
    try:
        path = transcript_path(session_id, cwd)
        if path is None:
            return None
        key = _stat_key(path)
        cached = _live_cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]

        sizes = [turn.context for turn in _read_tail_turns(path)]
        result = (
            LiveContext(size=sizes[-1], growth=sizes[-1] - sizes[-2] if len(sizes) > 1 else None, history=sizes)
            if sizes
            else None
        )
        _live_cache[path] = (key, result)
        return result
    except (OSError, ValueError):
        return None


def _read_tail_latest_timestamp(path: Path) -> Optional[datetime]:
    """The newest `user` line's timestamp near EOF, in a window that doubles until one is found.

    Only `user` lines count (a tool result, or something the person typed): those are what appear
    once a dialog has been answered. `assistant` lines and bookkeeping lines (`attachment`,
    `system`, ...) can be written while a dialog is still open, e.g. a later tool call of the same
    parallel batch still streaming in, and must not read as "the prompt was answered".
    """
    window = _TAIL_WINDOW
    with path.open("rb") as f:
        size = f.seek(0, os.SEEK_END)
        while True:
            start = max(0, size - window)
            f.seek(start)
            lines = f.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]  # the window probably began mid-record
            latest: Optional[datetime] = None
            for line in lines:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict) or entry.get("type") != "user":
                    continue
                stamp = scanner.parse_iso_timestamp(entry.get("timestamp"))
                if stamp is None:
                    continue
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                if latest is None or stamp > latest:
                    latest = stamp
            if latest is not None or start == 0:
                return latest
            window *= 2


# path -> (stat key at last read, latest timestamp)
_activity_cache: dict[Path, tuple[tuple[int, int], Optional[datetime]]] = {}


def latest_activity(session_id: str, cwd: str) -> Optional[datetime]:
    """When the session's transcript last got a `user` line (by the line's own timestamp), or None. Never raises.

    Lets the pending-prompt store tell that a session moved on (a tool result was written) after a
    prompt was registered - the line's timestamp, not the file's mtime, so a line flushed late but
    stamped before the prompt can't be mistaken for progress. Only `user` lines count; see
    `_read_tail_latest_timestamp`.
    """
    try:
        path = transcript_path(session_id, cwd)
        if path is None:
            return None
        key = _stat_key(path)
        cached = _activity_cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]

        latest = _read_tail_latest_timestamp(path)
        _activity_cache[path] = (key, latest)
        return latest
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- detail view


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


# ---------------------------------------------------------------- context breakdown

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


def _safe_breakdown(
    turns: list[Turn], compactions: list[Compaction], events: list[StartupEvent], session_id: str
) -> Optional[Breakdown]:
    """The breakdown, or None (logged) if it cannot be built, so a bad attachment never costs the detail view."""
    try:
        return build_breakdown(turns, compactions, events)
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        log.warning("context breakdown failed session_id=%s", session_id, exc_info=True)
        return None


def parse_detail(lines: Iterable[str], session_id: str = "") -> SessionDetail:
    turns, compactions, events = _scan(lines)
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
        path = transcript_path(session_id, cwd)
        if path is None:
            return None
        key = _stat_key(path)
        cached = _detail_cache.get(path)
        if cached is not None and cached[0] == key:
            return cached[1]

        with path.open("r", encoding="utf-8", errors="replace") as f:
            detail = parse_detail(f, session_id)
        _detail_cache[path] = (key, detail)
        return detail
    except (OSError, ValueError):
        return None
