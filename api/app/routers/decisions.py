"""Pending tool-permission prompts relayed from live sessions."""

from __future__ import annotations

from typing import Annotated, Any, Union

from fastapi import APIRouter, HTTPException, Path, Request

from app import deps
from app.core.security import is_local
from app.schemas.common import SESSION_ID_PATTERN, SessionId
from app.schemas.decisions import DecisionAnswer, DecisionRequest

router = APIRouter()


@router.post("/api/sessions/{session_id}/decisions")
async def post_decision(session_id: SessionId, body: DecisionRequest, request: Request) -> dict:
    """Called by the relay hook only. Registers the prompt and holds the request until it is
    answered, cleared or the wait elapses - `{decision: null}` then, and the hook prints nothing."""
    # The hook runs on this machine; a remote device has no business registering prompts (a forged
    # one could then be "answered" as if it were real).
    if not is_local(request):
        raise HTTPException(status_code=403, detail="registering a prompt requires a local request")
    return await deps.decisions.request_decision(session_id, body.tool_name, body.tool_input)


@router.get("/api/sessions/{session_id}/pending-decision")
def get_pending_decision(session_id: SessionId, request: Request) -> dict:
    deps.sweep_prompts()
    visible = deps.can_see_prompts(request)
    return {"pending_decision": deps.decisions.peek(session_id) if visible else None}


QUESTION_TOOL = "AskUserQuestion"


def _checked_answers(prompt: dict[str, Any], answers: dict[str, Union[str, list[str]]]) -> dict[str, Any]:
    """Validate a question's answers against the stored prompt; 422 when they don't fit it.

    Each of the prompt's questions needs exactly one answer keyed by its text: an option label or
    free text ("Other") as a string, or a list only where the question is multi-select.
    """
    asked = {
        q["question"]: bool(q.get("multiSelect"))
        for q in (prompt["tool_input"].get("questions") or [])
        if isinstance(q, dict) and isinstance(q.get("question"), str)
    }
    if not asked:
        raise HTTPException(status_code=422, detail="this prompt has no answerable questions")
    if set(answers) != set(asked):
        raise HTTPException(status_code=422, detail="answers must cover exactly the questions asked")
    for text, value in answers.items():
        if isinstance(value, list):
            if not asked[text]:
                raise HTTPException(status_code=422, detail=f"only a multi-select question takes a list: {text!r}")
            if not value or any(not item.strip() for item in value):
                raise HTTPException(status_code=422, detail=f"pick at least one non-blank option: {text!r}")
        elif not value.strip():
            raise HTTPException(status_code=422, detail=f"answer is blank: {text!r}")
    return {"decision": "answer", "answers": answers}


def _checked_answer(prompt: dict[str, Any], body: DecisionAnswer) -> dict[str, Any]:
    """The answer the hook receives, or a 422 when its shape doesn't fit the kind of prompt."""
    is_question = prompt["tool_name"] == QUESTION_TOOL
    if body.decision == "answer":
        if not is_question:
            raise HTTPException(status_code=422, detail="this is a permission prompt: answer allow or deny")
        if body.answers is None:
            raise HTTPException(status_code=422, detail="answers are required")
        return _checked_answers(prompt, body.answers)
    if is_question:
        raise HTTPException(status_code=422, detail="this is a question: answer with answers")
    if body.decision == "allow":
        return {"decision": "allow"}
    return {"decision": "deny", "reason": (body.reason or "").strip() or None}


@router.post("/api/sessions/{session_id}/decisions/{prompt_id}/answer")
def post_decision_answer(
    session_id: SessionId,
    prompt_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    body: DecisionAnswer,
    request: Request,
) -> dict:
    # Token and CSRF header were already checked by the middleware; Remote mode is the extra gate
    # for another device.
    if not deps.can_see_prompts(request):
        raise HTTPException(status_code=403, detail="Remote mode is off")
    deps.sweep_prompts()  # a prompt answered in the terminal a moment ago should 409, not "succeed"
    prompt = deps.decisions.get(session_id, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=409, detail="this session already moved on")
    answer = _checked_answer(prompt, body)
    # A plain `def` route runs in Starlette's threadpool; answer() wakes the hook's waiting request
    # on that request's own event loop, so calling it from here is safe.
    if not deps.decisions.answer(session_id, prompt_id, answer):
        raise HTTPException(status_code=409, detail="this session already moved on")
    return {"answered": prompt_id}
