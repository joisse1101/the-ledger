"""Dataclasses shared by the transcript-context modules."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Optional



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
    timestamp: Optional[datetime] = None


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
