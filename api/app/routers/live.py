"""The live sessions list."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import deps

router = APIRouter()


@router.get("/api/live")
def get_live(request: Request) -> dict:
    deps.sweep_prompts()
    visible = deps.can_see_prompts(request)
    return {
        "sessions": [
            {**item, "pending_decision": deps.decisions.peek(item["session_id"]) if visible else None}
            for item in deps.live.get()
        ]
    }
