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


def _current() -> dict:
    return settings_body(settings_service.get_worktree_folders(), settings_service.get_max_projects())


@router.get("/api/settings")
def get_settings(request: Request) -> dict:
    _require_local(request)
    return _current()


@router.put("/api/settings")
def put_settings(body: SettingsRequest, request: Request) -> dict:
    _require_local(request)
    max_projects = body.widget.max_projects if body.widget else None
    settings_service.save_settings(body.worktree_folders, max_projects)
    return _current()
