"""Switching Remote mode and reading its sign-in code."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.security import is_local
from app.schemas.remote import RemoteModeRequest
from app.services import remote_service

router = APIRouter()


@router.post("/api/remote-mode")
def post_remote_mode(body: RemoteModeRequest, request: Request) -> dict:
    # Same locality test as the delete routes: a valid token lets another device see and answer
    # prompts while Remote mode is on, but never lets it change Remote mode itself.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="switching Remote mode requires a local request")
    return remote_service.set_enabled(body.enabled)


@router.get("/api/remote-mode/qr")
def get_remote_mode_qr(request: Request) -> dict:
    # The code contains the access token, so even a valid token isn't enough to read it.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="the sign-in code requires a local request")
    return remote_service.sign_in_code()
