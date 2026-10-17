"""Pending tool-permission prompts relayed from live sessions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Request

from app.core.security import is_local
from app.schemas.common import SESSION_ID_PATTERN, SessionId
from app.schemas.decisions import DecisionAnswer, DecisionRequest
from app.services import decision_service, prompt_service

router = APIRouter()


@router.post("/api/sessions/{session_id}/decisions")
async def post_decision(session_id: SessionId, body: DecisionRequest, request: Request) -> dict:
    """Called by the relay hook only. Registers the prompt and holds the request until it is
    answered, cleared or the wait elapses - `{decision: null}` then, and the hook prints nothing."""
    # The hook runs on this machine; a remote device has no business registering prompts (a forged
    # one could then be "answered" as if it were real).
    if not is_local(request):
        raise HTTPException(status_code=403, detail="registering a prompt requires a local request")
    return await prompt_service.register(session_id, body.tool_name, body.tool_input)


@router.get("/api/sessions/{session_id}/pending-decision")
def get_pending_decision(session_id: SessionId, request: Request) -> dict:
    return {"pending_decision": prompt_service.pending_for(session_id, is_local(request))}


@router.post("/api/sessions/{session_id}/decisions/{prompt_id}/answer")
def post_decision_answer(
    session_id: SessionId,
    prompt_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    body: DecisionAnswer,
    request: Request,
) -> dict:
    # Token and CSRF header were already checked by the middleware; Remote mode is the extra gate
    # for another device.
    if not prompt_service.can_see(is_local(request)):
        raise HTTPException(status_code=403, detail="Remote mode is off")
    decision_service.answer_prompt(session_id, prompt_id, body.decision, body.answers, body.reason)
    return {"answered": prompt_id}
