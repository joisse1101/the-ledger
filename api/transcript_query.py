"""Search, filter, sort and paging for the All-sessions list.

Plain Python over `ClaudeTranscript`s, so the API sends the browser one page at a
time instead of the whole history (and its 600-character snippets).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from claude_transcripts import ClaudeTranscript

# Sortable fields, by the name the API and UI use for them.
SORT_FIELDS = (
    "project",
    "title",
    "session_id",
    "started_at",
    "updated_at",
    "message_count",
    "cost",
    "context",
    "version",
    "git_branch",
)
DEFAULT_SORT = "updated_at"
DEFAULT_PAGE_SIZE = 50


@dataclass
class Page:
    items: list[ClaudeTranscript]
    total: int  # sessions matching the filters, not just this page
    options: dict[str, list[str]]  # distinct filter values, over the unfiltered list


def _contains(haystack: str, needle: str) -> bool:
    return needle in haystack.casefold()


def filter_transcripts(
    transcripts: Sequence[ClaudeTranscript],
    *,
    search: str = "",
    projects: Sequence[str] = (),
    versions: Sequence[str] = (),
    branches: Sequence[str] = (),
) -> list[ClaudeTranscript]:
    """Sessions matching every given filter.

    - `search` is a case-insensitive *literal* substring (no regex/wildcards) of the
      session ID, last message or first prompt.
    - Each selected list matches any of its values; the four conditions combine with AND.
    """
    needle = search.casefold()
    project_set, version_set, branch_set = set(projects), set(versions), set(branches)
    result = []
    for transcript in transcripts:
        if needle and not (
            _contains(transcript.session_id, needle)
            or _contains(transcript.last_message, needle)
            or _contains(transcript.first_prompt, needle)
        ):
            continue
        if project_set and transcript.project not in project_set:
            continue
        if version_set and transcript.version not in version_set:
            continue
        if branch_set and transcript.git_branch not in branch_set:
            continue
        result.append(transcript)
    return result


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def sort_transcripts(
    transcripts: Sequence[ClaudeTranscript], sort: str, ascending: bool
) -> list[ClaudeTranscript]:
    """Stable sort by `sort`; sessions with no value for it come last either way."""
    if sort not in SORT_FIELDS:
        raise ValueError(f"unknown sort field: {sort!r}")
    present, missing = [], []
    for transcript in transcripts:
        (missing if _is_missing(getattr(transcript, sort)) else present).append(transcript)
    # reverse=True keeps equal elements in their original order, so ties stay stable.
    present.sort(key=lambda transcript: getattr(transcript, sort), reverse=not ascending)
    return present + missing


def _distinct(values: Sequence[Optional[str]]) -> list[str]:
    return sorted({value for value in values if value and value.strip()})


def filter_options(transcripts: Sequence[ClaudeTranscript]) -> dict[str, list[str]]:
    """Distinct, non-blank projects/versions/branches, for the filter pickers."""
    return {
        "projects": _distinct([t.project for t in transcripts]),
        "versions": _distinct([t.version for t in transcripts]),
        "branches": _distinct([t.git_branch for t in transcripts]),
    }


def query(
    transcripts: Sequence[ClaudeTranscript],
    *,
    search: str = "",
    projects: Sequence[str] = (),
    versions: Sequence[str] = (),
    branches: Sequence[str] = (),
    sort: str = DEFAULT_SORT,
    ascending: bool = False,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> Page:
    matched = filter_transcripts(
        transcripts, search=search, projects=projects, versions=versions, branches=branches
    )
    ordered = sort_transcripts(matched, sort, ascending)
    return Page(
        items=ordered[offset : offset + limit],
        total=len(ordered),
        options=filter_options(transcripts),
    )
