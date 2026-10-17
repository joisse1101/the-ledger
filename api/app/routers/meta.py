"""Snapshot metadata and the manual rescan."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app import deps, refresh
from app.core.security import is_local
from app.repositories import claude_db
from app.schemas.common import iso

router = APIRouter()


@router.get("/api/meta")
def get_meta(request: Request) -> dict:
    return {
        "refreshed_at": iso(claude_db.refreshed_at()),
        "is_local": is_local(request),
        "remote_mode": deps.remote_mode_status(),
    }


@router.post("/api/refresh")
def post_refresh() -> dict:
    return {"refreshed_at": iso(refresh.locked_refresh())}
