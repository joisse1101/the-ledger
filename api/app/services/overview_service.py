"""The Overview page's stats for a validated filter."""

from __future__ import annotations

from typing import Optional

from app.domain import overview_stats
from app.repositories import claude_projects, claude_transcripts
from app.repositories.db import paths
from app.services.errors import InvalidInput, NotFound


DEFAULT_BUCKET_MINUTES = overview_stats.BUCKET_MINUTES


def get_overview(range_: str, project: Optional[str], group_by: str, bucket_minutes: int) -> dict:
    if bucket_minutes not in overview_stats.BUCKET_SIZES:
        raise InvalidInput(f"unknown bucket_minutes: {bucket_minutes!r}")
    if range_ not in overview_stats.TIME_RANGES:
        raise InvalidInput(f"unknown range: {range_!r}")
    if group_by not in overview_stats.GROUP_KEYS:
        raise InvalidInput(f"unknown group_by: {group_by!r}")
    folder = None
    if project is not None:
        # Matched exactly against the snapshot, like DELETE /api/projects; the folder is derived
        # server-side, never taken from the request.
        if project not in {p.path for p in claude_projects.load_projects()}:
            raise NotFound("unknown project")
        folder = paths.sanitize_project_path(project)
    return overview_stats.overview(
        claude_transcripts.load_transcripts(), range_, folder, group_by, bucket_minutes
    )
