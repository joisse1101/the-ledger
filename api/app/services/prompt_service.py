"""Who may see pending prompts, and keeping the pending list current."""

from __future__ import annotations

from typing import Optional

from app import deps


def sweep() -> None:
    """Drop every pending prompt whose session already moved on (answered in the terminal, say).

    Run ahead of each read/answer of the pending prompts rather than on a timer of its own: a
    prompt only matters while something is polling, and the transcript reads it costs are cached
    by file stat.
    """
    deps.decisions.sweep(deps.live.latest_activity)


def can_see(local: bool) -> bool:
    """The machine's own browser always sees pending prompts; another device only while Remote mode is on."""
    return local or deps.decisions.remote_mode_enabled()


def pending_for(session_id: str, local: bool) -> Optional[dict]:
    sweep()
    return deps.decisions.peek(session_id) if can_see(local) else None


def live_with_prompts(local: bool) -> list[dict]:
    sweep()
    visible = can_see(local)
    live = deps.live.get()
    deps.decisions.prune_auto_approve(item["session_id"] for item in live)
    return [
        {
            **item,
            "pending_decision": deps.decisions.peek(item["session_id"]) if visible else None,
            "auto_approve": deps.decisions.auto_approve_enabled(item["session_id"]),
            "last_auto_approved": deps.decisions.last_auto_approved(item["session_id"]),
        }
        for item in live
    ]


def relay_hook_seen() -> bool:
    """Whether any prompt has been relayed since the backend started."""
    return deps.decisions.relay_hook_seen()


async def register(session_id: str, tool_name: str, tool_input: dict) -> dict:
    """Register a prompt and hold until it is answered, cleared or the wait elapses."""
    return await deps.decisions.request_decision(session_id, tool_name, tool_input)
