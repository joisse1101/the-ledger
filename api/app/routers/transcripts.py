"""The paged, filterable list of every session."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.schemas.transcripts import transcript_item
from app.services import transcript_service

router = APIRouter()


SortField = Literal[
    "project", "title", "session_id", "started_at", "updated_at",
    "message_count", "cost", "context", "model", "used_openspec", "version", "git_branch",
    "worktree",
]


@router.get("/api/transcripts")
def get_transcripts(
    q: str = "",
    project: Annotated[list[str], Query()] = [],
    version: Annotated[list[str], Query()] = [],
    branch: Annotated[list[str], Query()] = [],
    worktree: Annotated[list[str], Query()] = [],
    sort: SortField = "updated_at",
    dir: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = transcript_service.DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    result = transcript_service.list_transcripts(
        q, project, version, branch, worktree, sort, dir == "asc", limit, offset
    )
    return {
        "items": [transcript_item(t, result.live_ids) for t in result.page.items],
        "total": result.page.total,
        "options": result.page.options,
    }
