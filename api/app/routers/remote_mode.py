"""Switching Remote mode and reading its sign-in code."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

import gateway_signin
from app import deps
from app.core.security import is_local
from app.infra import banner
from app.schemas.remote import RemoteModeRequest

router = APIRouter()


@router.post("/api/remote-mode")
def post_remote_mode(body: RemoteModeRequest, request: Request) -> dict:
    # Same locality test as the delete routes: a valid token lets another device see and answer
    # prompts while Remote mode is on, but never lets it change Remote mode itself.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="switching Remote mode requires a local request")
    if deps.remote is None:
        raise HTTPException(status_code=503, detail="Remote mode is not available yet")
    if body.enabled:
        deps.remote.start()  # returns at once; clients watch the state in /api/meta
    else:
        deps.remote.stop()
    return deps.remote_mode_status()


@router.get("/api/remote-mode/qr")
def get_remote_mode_qr(request: Request) -> dict:
    # The code contains the access token, so even a valid token isn't enough to read it.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="the sign-in code requires a local request")
    if deps.remote is None or not deps.remote.is_ready():
        raise HTTPException(status_code=409, detail="Remote mode is not ready")
    addresses = banner.discover_ipv4()
    if not addresses or deps.access_token is None:
        raise HTTPException(status_code=409, detail="No network address was found for this machine")
    svg = banner.render_qr_svg(gateway_signin.signin_url(addresses[0], deps.gateway_port, deps.access_token))
    if svg is None:
        raise HTTPException(status_code=503, detail="QR codes are unavailable (the qrcode package is missing)")
    return {
        "svg": svg,
        "display_url": gateway_signin.display_url(addresses[0], deps.gateway_port),
        "expires_at": deps.decisions.remote_mode()["expires_at"],
    }
