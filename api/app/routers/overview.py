"""The Overview page's aggregate stats."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query

from app.domain import overview_stats
from app.repositories import claude_db, claude_projects, claude_transcripts

router = APIRouter()


@router.get("/api/overview")
def get_overview(
    range_: Annotated[str, Query(alias="range")] = "All time",
    project: Optional[str] = None,
    group_by: str = "project",
    bucket_minutes: int = overview_stats.BUCKET_MINUTES,
) -> dict:
    if bucket_minutes not in overview_stats.BUCKET_SIZES:
        raise HTTPException(status_code=422, detail=f"unknown bucket_minutes: {bucket_minutes!r}")
    if range_ not in overview_stats.TIME_RANGES:
        raise HTTPException(status_code=422, detail=f"unknown range: {range_!r}")
    if group_by not in overview_stats.GROUP_KEYS:
        raise HTTPException(status_code=422, detail=f"unknown group_by: {group_by!r}")
    folder = None
    if project is not None:
        # Matched exactly against the snapshot, like DELETE /api/projects; the folder is derived
        # server-side, never taken from the request.
        if project not in {p.path for p in claude_projects.load_projects()}:
            raise HTTPException(status_code=404, detail="unknown project")
        folder = claude_db.sanitize_project_path(project)
    return overview_stats.overview(
        claude_transcripts.load_transcripts(), range_, folder, group_by, bucket_minutes
    )
