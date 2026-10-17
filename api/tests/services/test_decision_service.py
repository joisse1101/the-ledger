"""Answer validation for pending prompts, without HTTP."""

import pytest

from app.services.decision_service import _checked_answer
from app.services.errors import InvalidInput

QUESTION = {
    "tool_name": "AskUserQuestion",
    "tool_input": {"questions": [{"question": "Which?", "multiSelect": False}]},
}
PERMISSION = {"tool_name": "Bash", "tool_input": {"command": "ls"}}


def test_allow_and_deny_on_a_permission_prompt():
    assert _checked_answer(PERMISSION, "allow", None, None) == {"decision": "allow"}
    assert _checked_answer(PERMISSION, "deny", None, "  no  ") == {"decision": "deny", "reason": "no"}
    assert _checked_answer(PERMISSION, "deny", None, " ") == {"decision": "deny", "reason": None}


def test_question_takes_answers_keyed_by_its_text():
    assert _checked_answer(QUESTION, "answer", {"Which?": "A"}, None) == {
        "decision": "answer",
        "answers": {"Which?": "A"},
    }


@pytest.mark.parametrize(
    ("prompt", "decision", "answers"),
    [
        (PERMISSION, "answer", {"x": "y"}),
        (QUESTION, "allow", None),
        (QUESTION, "answer", None),
        (QUESTION, "answer", {"Other?": "A"}),
        (QUESTION, "answer", {"Which?": " "}),
        (QUESTION, "answer", {"Which?": ["A"]}),
    ],
)
def test_mismatched_answers_are_invalid(prompt, decision, answers):
    with pytest.raises(InvalidInput):
        _checked_answer(prompt, decision, answers, None)
