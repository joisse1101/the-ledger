"""The paged, filterable list of every session."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app import deps
from app.domain import transcript_query
from app.repositories import claude_transcripts
from app.schemas.transcripts import transcript_item

router = APIRouter()


SortField = Literal[
    "project", "title", "session_id", "started_at", "updated_at",
    "message_count", "cost", "context", "model", "used_openspec", "version", "git_branch",
]


@router.get("/api/transcripts")
def get_transcripts(
    q: str = "",
    project: Annotated[list[str], Query()] = [],
    version: Annotated[list[str], Query()] = [],
    branch: Annotated[list[str], Query()] = [],
    sort: SortField = "updated_at",
    dir: Literal["asc", "desc"] = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = transcript_query.DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    page = transcript_query.query(
        claude_transcripts.load_transcripts(),
        search=q,
        projects=project,
        versions=version,
        branches=branch,
        sort=sort,
        ascending=dir == "asc",
        limit=limit,
        offset=offset,
    )
    live_ids = deps.live.live_ids()
    return {
        "items": [transcript_item(t, live_ids) for t in page.items],
        "total": page.total,
        "options": page.options,
    }
