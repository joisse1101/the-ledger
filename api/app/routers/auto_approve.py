"""Switching a live session's auto-approve."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.security import is_local
from app.schemas.auto_approve import AutoApproveRequest
from app.schemas.common import SessionId
from app.services import auto_approve_service

router = APIRouter()


@router.post("/api/sessions/{session_id}/auto-approve")
def post_auto_approve(session_id: SessionId, body: AutoApproveRequest, request: Request) -> dict:
    # Like Remote mode: a valid token lets another device see the state, never change it.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="switching auto-approve requires a local request")
    return auto_approve_service.set_enabled(session_id, body.enabled)
