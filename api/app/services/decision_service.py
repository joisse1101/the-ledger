"""Answering a pending prompt: check the answer fits the prompt, then hand it to the waiting hook."""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from app import deps
from app.services.errors import Conflict, InvalidInput

QUESTION_TOOL = "AskUserQuestion"

Answers = dict[str, Union[str, list[str]]]


def _checked_answers(prompt: dict[str, Any], answers: Answers) -> dict[str, Any]:
    """Validate a question's answers against the stored prompt.

    Each of the prompt's questions needs exactly one answer keyed by its text: an option label or
    free text ("Other") as a string, or a list only where the question is multi-select.
    """
    asked = {
        q["question"]: bool(q.get("multiSelect"))
        for q in (prompt["tool_input"].get("questions") or [])
        if isinstance(q, dict) and isinstance(q.get("question"), str)
    }
    if not asked:
        raise InvalidInput("this prompt has no answerable questions")
    if set(answers) != set(asked):
        raise InvalidInput("answers must cover exactly the questions asked")
    for text, value in answers.items():
        if isinstance(value, list):
            if not asked[text]:
                raise InvalidInput(f"only a multi-select question takes a list: {text!r}")
            if not value or any(not item.strip() for item in value):
                raise InvalidInput(f"pick at least one non-blank option: {text!r}")
        elif not value.strip():
            raise InvalidInput(f"answer is blank: {text!r}")
    return {"decision": "answer", "answers": answers}


def _checked_answer(
    prompt: dict[str, Any],
    decision: Literal["allow", "deny", "answer"],
    answers: Optional[Answers],
    reason: Optional[str],
) -> dict[str, Any]:
    """The answer the hook receives; InvalidInput when its shape doesn't fit the kind of prompt."""
    is_question = prompt["tool_name"] == QUESTION_TOOL
    if decision == "answer":
        if not is_question:
            raise InvalidInput("this is a permission prompt: answer allow or deny")
        if answers is None:
            raise InvalidInput("answers are required")
        return _checked_answers(prompt, answers)
    if is_question:
        raise InvalidInput("this is a question: answer with answers")
    if decision == "allow":
        return {"decision": "allow"}
    return {"decision": "deny", "reason": (reason or "").strip() or None}


def answer_prompt(
    session_id: str,
    prompt_id: str,
    decision: Literal["allow", "deny", "answer"],
    answers: Optional[Answers],
    reason: Optional[str],
) -> None:
    deps.sweep_prompts()  # a prompt answered in the terminal a moment ago should 409, not "succeed"
    prompt = deps.decisions.get(session_id, prompt_id)
    if prompt is None:
        raise Conflict("this session already moved on")
    answer = _checked_answer(prompt, decision, answers, reason)
    # A plain `def` route runs in Starlette's threadpool; answer() wakes the hook's waiting request
    # on that request's own event loop, so calling it from here is safe.
    if not deps.decisions.answer(session_id, prompt_id, answer):
        raise Conflict("this session already moved on")
