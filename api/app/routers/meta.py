"""Snapshot metadata and the manual rescan."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.security import is_local
from app.schemas.common import iso
from app.services import project_repo_service, prompt_service, remote_service, snapshot_service

router = APIRouter()


@router.get("/api/meta")
def get_meta(request: Request) -> dict:
    return {
        "refreshed_at": iso(snapshot_service.refreshed_at()),
        "is_local": is_local(request),
        "remote_mode": remote_service.remote_mode_status(),
        "relay_hook_seen": prompt_service.relay_hook_seen(),
    }


@router.post("/api/refresh")
def post_refresh() -> dict:
    # Repo counts are fetched lazily by GET /api/projects/repos; dropping the cache makes the next
    # read hit git and gh, and keeps a failing gh from failing the rescan.
    project_repo_service.clear_cache()
    return {"refreshed_at": iso(snapshot_service.rescan())}
