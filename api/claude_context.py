"""Live context size and per-session token history, read straight from a session's transcript.

Like `claude_sessions.py`, this deliberately bypasses the SQLite snapshot in `claude_db.py`: the
Live table polls every 2s, and a snapshot that only refreshes on demand would leave the gauge stale
(and blank for brand-new sessions). Everything here is absolute tokens - the transcript doesn't say
what a model's context window is, so nothing is expressed as a percentage of a limit.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import claude_db

SPARKLINE_TURNS = 24
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
class SessionDetail:
    turns: list[Turn]
    compactions: list[Compaction]
    attribution: Attribution


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


def _scan(lines: Iterable[str]) -> tuple[list[Turn], list[Compaction]]:
    turns: dict[str, Turn] = {}
    compactions: list[Compaction] = []

    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
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
            timestamp=claude_db._parse_iso_timestamp(entry.get("timestamp")),
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

    return list(turns.values()), compactions


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
    root = claude_db.projects_dir()
    direct = root / claude_db.sanitize_project_path(cwd) / f"{session_id}.jsonl"
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


# ---------------------------------------------------------------- detail view


def is_cache_miss(index: int, turn: Turn) -> bool:
    """A response other than the first that wrote more cache than it read (a fresh session's first one always does)."""
    return index > 0 and turn.cache_written > turn.cache_read


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
        tool = previous.tools[0] if previous.tools else ToolUse(_NO_TOOL_LABEL)
        delta = segment[offset].context - previous.context
        entry = totals.setdefault(tool.name, [0, 0])
        entry[0] += delta
        entry[1] += 1
        if delta > 0:
            increases.append(Increase(index=start + offset, tokens=delta, tool=tool.name, hint=tool.hint))

    by_tool = sorted((ToolGrowth(name, tokens, uses) for name, (tokens, uses) in totals.items()), key=lambda g: -g.tokens)
    increases.sort(key=lambda inc: -inc.tokens)  # stable: ties keep chronological order
    return Attribution(floor=segment[0].context, current=segment[-1].context, by_tool=by_tool, largest=increases[:_TOP_INCREASES])


def parse_detail(lines: Iterable[str]) -> SessionDetail:
    turns, compactions = _scan(lines)
    for index, turn in enumerate(turns):
        turn.cache_miss = is_cache_miss(index, turn)
    return SessionDetail(turns=turns, compactions=compactions, attribution=attribute_growth(turns, compactions))


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
            detail = parse_detail(f)
        _detail_cache[path] = (key, detail)
        return detail
    except (OSError, ValueError):
        return None
