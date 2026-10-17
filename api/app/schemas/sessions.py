"""The JSON shape of a session's context detail."""

from __future__ import annotations

from typing import Optional

from app.domain import claude_context
from app.repositories import claude_transcripts
from app.schemas.common import iso

def breakdown_json(breakdown: Optional[claude_context.Breakdown]) -> Optional[dict]:
    if breakdown is None:
        return None
    return {
        "snapshots": [
            {
                "position": snapshot.position,
                "categories": [
                    {
                        "name": category.name,
                        "tokens": category.tokens,
                        "items": [{"label": item.label, "tokens": item.tokens} for item in category.items],
                    }
                    for category in snapshot.categories
                ],
            }
            for snapshot in breakdown.snapshots
        ],
        "turns": [
            {
                "snapshot": row.snapshot,
                "growth": [{"tool": g.tool, "tokens": g.tokens} for g in row.growth],
                "remainder": row.remainder,
            }
            for row in breakdown.turns
        ],
    }


def detail_json(detail: claude_context.SessionDetail) -> dict:
    attribution = detail.attribution
    return {
        "turns": [
            {
                "message_id": turn.message_id,
                "timestamp": iso(turn.timestamp),
                "new": turn.new,
                "cache_read": turn.cache_read,
                "cache_written": turn.cache_written,
                "output": turn.output,
                "context": turn.context,
                "tools": [{"name": tool.name, "hint": tool.hint} for tool in turn.tools],
                "cache_miss": turn.cache_miss,
            }
            for turn in detail.turns
        ],
        "compactions": [
            {"position": c.position, "trigger": c.trigger, "pre_tokens": c.pre_tokens}
            for c in detail.compactions
        ],
        "attribution": {
            "floor": attribution.floor,
            "current": attribution.current,
            "by_tool": [{"tool": g.tool, "tokens": g.tokens, "uses": g.uses} for g in attribution.by_tool],
            "largest": [
                {"index": i.index, "tokens": i.tokens, "tool": i.tool, "hint": i.hint}
                for i in attribution.largest
            ],
        },
        "breakdown": breakdown_json(detail.breakdown),
    }


def recap_json(transcript: Optional[claude_transcripts.ClaudeTranscript], live_item: Optional[dict]) -> Optional[dict]:
    """The dialog's header facts, from the snapshot row if there is one, else the live registry."""
    if transcript is not None:
        context = transcript.context
        messages = transcript.message_count
        recap = {
            "title": transcript.title,
            "last_message": transcript.last_message,
            "first_prompt": transcript.first_prompt,
            "started_at": iso(transcript.started_at),
            "updated_at": iso(transcript.updated_at),
            "message_count": messages,
            "cost": transcript.cost,
            "cost_source": transcript.cost_source,
            "unpriced_models": transcript.unpriced_models,
            "cost_state_flagged": transcript.cost_state_flagged,
        }
    elif live_item is not None:
        # Brand new: the registry knows it, the snapshot doesn't yet.
        context = live_item["context"]["size"] if live_item["context"] else None
        messages = None
        recap = {
            "title": live_item["title"],
            "last_message": live_item["last_message"],
            "first_prompt": live_item["first_prompt"],
            "started_at": live_item["started_at"],
            "updated_at": live_item["updated_at"],
            "message_count": None,
            "cost": None,
            "cost_source": None,
            "unpriced_models": [],
            "cost_state_flagged": False,
        }
    else:
        return None
    recap["context"] = context
    recap["avg_tokens_per_message"] = round(context / messages) if context and messages else None
    return recap
