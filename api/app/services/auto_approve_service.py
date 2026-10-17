"""Switching auto-approve for one live session."""

from __future__ import annotations

from app import deps
from app.services.errors import NotFound


def set_enabled(session_id: str, enabled: bool) -> dict:
    """Switch the session's auto-approve and, when turning it on, approve what is already waiting.

    The flag is set before the pending prompts are scanned; request_decision() registers a prompt
    before it checks the flag. Whichever order a racing prompt and this switch land in, one side
    approves it, and the other finds it already answered.
    """
    if not deps.live.is_live_now(session_id):
        raise NotFound("this session is not live")
    deps.decisions.set_auto_approve(session_id, enabled)
    if enabled:
        deps.decisions.approve_pending(session_id)
    return {"auto_approve": deps.decisions.auto_approve_enabled(session_id)}
