"""The live sessions list."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.security import is_local
from app.services import prompt_service

router = APIRouter()


@router.get("/api/live")
def get_live(request: Request) -> dict:
    return {"sessions": prompt_service.live_with_prompts(is_local(request))}
