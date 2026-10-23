"""The sessions list: filtered, sorted and paged, with each row's live flag."""

from __future__ import annotations

from dataclasses import dataclass

from app import deps
from app.domain import transcript_query
from app.repositories import claude_transcripts

DEFAULT_PAGE_SIZE = transcript_query.DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class TranscriptPage:
    page: transcript_query.Page
    live_ids: set[str]


def list_transcripts(
    q: str,
    projects: list[str],
    versions: list[str],
    branches: list[str],
    worktrees: list[str],
    sort: str,
    ascending: bool,
    limit: int,
    offset: int,
) -> TranscriptPage:
    page = transcript_query.query(
        claude_transcripts.load_transcripts(),
        search=q,
        projects=projects,
        versions=versions,
        branches=branches,
        worktrees=worktrees,
        sort=sort,
        ascending=ascending,
        limit=limit,
        offset=offset,
    )
    return TranscriptPage(page=page, live_ids=deps.live.live_ids())
