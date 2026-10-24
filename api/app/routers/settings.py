"""Dashboard settings: readable and changeable only from the machine running the app."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.security import is_local
from app.schemas.settings import SettingsRequest, settings_body
from app.services import settings_service

router = APIRouter()


def _require_local(request: Request) -> None:
    # A valid token lets another device read the dashboard, never its settings.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="settings require a local request")


@router.get("/api/settings")
def get_settings(request: Request) -> dict:
    _require_local(request)
    return settings_body(settings_service.get_worktree_folders())


@router.put("/api/settings")
def put_settings(body: SettingsRequest, request: Request) -> dict:
    _require_local(request)
    return settings_body(settings_service.save_worktree_folders(body.worktree_folders))
