"""Request bodies for the pending-prompt routes."""

from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel

class DecisionRequest(BaseModel):
    tool_name: str
    tool_input: dict


class DecisionAnswer(BaseModel):
    decision: Literal["allow", "deny", "answer"]
    reason: Optional[str] = None
    answers: Optional[dict[str, Union[str, list[str]]]] = None
