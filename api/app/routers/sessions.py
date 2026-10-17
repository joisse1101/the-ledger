"""One session's detail, its deletion and opening its repo."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.security import is_local
from app.schemas.common import SessionId
from app.schemas.sessions import detail_json, recap_json
from app.services import session_service

router = APIRouter()


@router.get("/api/sessions/{session_id}")
def get_session(session_id: SessionId) -> dict:
    view = session_service.get_session(session_id)
    return {
        "session_id": session_id,
        "live": view.live,
        "recap": recap_json(view.transcript, view.live_item),
        "readable": view.detail is not None,
        "detail": detail_json(view.detail) if view.detail is not None else None,
    }


@router.delete("/api/sessions/{session_id}")
def delete_session(session_id: SessionId, request: Request) -> dict:
    # A valid token widens what a remote device can read/trigger, but never authorizes a delete.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
    session_service.delete_session(session_id)
    return {"deleted": session_id}


@router.post("/api/sessions/{session_id}/open-repo")
def post_open_repo(session_id: SessionId) -> dict:
    session_service.open_repo(session_id)
    return {"opened": session_id}
