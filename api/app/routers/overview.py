"""The Overview page's aggregate stats."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Query

from app.services import overview_service

router = APIRouter()


@router.get("/api/overview")
def get_overview(
    range_: Annotated[str, Query(alias="range")] = "All time",
    project: Optional[str] = None,
    group_by: str = "project",
    bucket_minutes: int = overview_service.DEFAULT_BUCKET_MINUTES,
) -> dict:
    return overview_service.get_overview(range_, project, group_by, bucket_minutes)
