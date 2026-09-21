"""FastAPI server for the dashboard: a JSON API over the claude_* data modules."""

from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Literal, Optional

from fastapi import FastAPI, HTTPException, Path, Query

import claude_context
import claude_db
import claude_projects
import claude_transcripts
import overview_stats
import transcript_query
from live_snapshot import LiveSnapshot

log = logging.getLogger("ledger")

# The background rescan runs every 10 minutes for as long as the server is up.
REFRESH_INTERVAL_SECONDS = 10 * 60

# refresh() rewrites both tables and can take seconds on a big history, so it is
# serialised process-wide: startup, the timer and POST /api/refresh never overlap.
_refresh_lock = threading.Lock()

# The one place the live registry is read from; see live_snapshot.py.
live = LiveSnapshot()


def locked_refresh() -> datetime:
    with _refresh_lock:
        return claude_db.refresh()


def _startup_snapshot() -> None:
    with _refresh_lock:
        claude_db.startup()


async def refresh_loop(interval: float = REFRESH_INTERVAL_SECONDS) -> None:
    """Rescan every `interval` seconds, in a worker thread, until cancelled."""
    while True:
        await asyncio.sleep(interval)
        try:
            await asyncio.to_thread(locked_refresh)
        except Exception:
            # A bad scan must not end the loop; the next tick tries again.
            log.exception("background refresh failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(_startup_snapshot)
    task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="The Ledger",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


@app.get("/api/meta")
def get_meta() -> dict:
    return {"refreshed_at": _iso(claude_db.refreshed_at())}


@app.post("/api/refresh")
def post_refresh() -> dict:
    return {"refreshed_at": _iso(locked_refresh())}


@app.get("/api/live")
def get_live() -> dict:
    return {"sessions": live.get()}


def _transcript_item(transcript: claude_transcripts.ClaudeTranscript, live_ids: set[str]) -> dict:
    return {
        "session_id": transcript.session_id,
        "project": transcript.project,
        "title": transcript.title,
        "started_at": _iso(transcript.started_at),
        "updated_at": _iso(transcript.updated_at),
        "message_count": transcript.message_count,
        "cost": transcript.cost,
        "context": transcript.context,
        "version": transcript.version,
        "git_branch": transcript.git_branch,
        "live": transcript.session_id in live_ids,
    }


SortField = Literal[
    "project", "title", "session_id", "started_at", "updated_at",
    "message_count", "cost", "context", "version", "git_branch",
]


@app.get("/api/transcripts")
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
    live_ids = live.live_ids()
    return {
        "items": [_transcript_item(t, live_ids) for t in page.items],
        "total": page.total,
        "options": page.options,
    }


# Real session IDs are UUIDs. Anything else never reaches a path or a query.
SESSION_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"
SessionId = Annotated[str, Path(pattern=SESSION_ID_PATTERN)]


def _find_transcript(session_id: str) -> Optional[claude_transcripts.ClaudeTranscript]:
    return next((t for t in claude_transcripts.load_transcripts() if t.session_id == session_id), None)


def _recap(transcript: Optional[claude_transcripts.ClaudeTranscript], live_item: Optional[dict]) -> Optional[dict]:
    """The dialog's header facts, from the snapshot row if there is one, else the live registry."""
    if transcript is not None:
        context = transcript.context
        messages = transcript.message_count
        recap = {
            "title": transcript.title,
            "last_message": transcript.last_message,
            "first_prompt": transcript.first_prompt,
            "started_at": _iso(transcript.started_at),
            "updated_at": _iso(transcript.updated_at),
            "message_count": messages,
            "cost": transcript.cost,
        }
    elif live_item is not None:
        # Brand new: the registry knows it, the snapshot doesn't yet.
        context = live_item["context"]["size"] if live_item["context"] else None
        messages = None
        recap = {
            "title": live_item["title"],
            "last_message": live_item["last_message"],
            "first_prompt": live_item["first_prompt"],
            "started_at": live_item["started_at"],
            "updated_at": live_item["updated_at"],
            "message_count": None,
            "cost": None,
        }
    else:
        return None
    recap["context"] = context
    recap["avg_tokens_per_message"] = round(context / messages) if context and messages else None
    return recap


def _detail_json(detail: claude_context.SessionDetail) -> dict:
    attribution = detail.attribution
    return {
        "turns": [
            {
                "message_id": turn.message_id,
                "timestamp": _iso(turn.timestamp),
                "new": turn.new,
                "cache_read": turn.cache_read,
                "cache_written": turn.cache_written,
                "output": turn.output,
                "context": turn.context,
                "tools": [{"name": tool.name, "hint": tool.hint} for tool in turn.tools],
                "cache_miss": turn.cache_miss,
            }
            for turn in detail.turns
        ],
        "compactions": [
            {"position": c.position, "trigger": c.trigger, "pre_tokens": c.pre_tokens}
            for c in detail.compactions
        ],
        "attribution": {
            "floor": attribution.floor,
            "current": attribution.current,
            "by_tool": [{"tool": g.tool, "tokens": g.tokens, "uses": g.uses} for g in attribution.by_tool],
            "largest": [
                {"index": i.index, "tokens": i.tokens, "tool": i.tool, "hint": i.hint}
                for i in attribution.largest
            ],
        },
    }


@app.get("/api/sessions/{session_id}")
def get_session(session_id: SessionId) -> dict:
    # The working directory is only ever taken from the registry or the snapshot,
    # never from the request, so a client can't point the transcript lookup elsewhere.
    transcript = _find_transcript(session_id)
    live_ids = live.live_ids()
    live_item = next((s for s in live.get() if s["session_id"] == session_id), None)
    cwd = live.cwd_for(session_id) or (transcript.cwd if transcript else None)
    if cwd is None:
        raise HTTPException(status_code=404, detail="unknown session")

    detail = claude_context.load_detail(session_id, cwd)
    return {
        "session_id": session_id,
        "live": session_id in live_ids,
        "recap": _recap(transcript, live_item),
        "readable": detail is not None,
        "detail": _detail_json(detail) if detail is not None else None,
    }


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: SessionId) -> dict:
    # Liveness comes from a fresh registry read: the 1s cached list could still say
    # "not live" for a session that started a moment ago.
    if live.is_live_now(session_id):
        raise HTTPException(status_code=409, detail="session is live and cannot be deleted")
    with _refresh_lock:  # a concurrent rescan could otherwise re-add the row
        if claude_db.transcript_path_for_session(session_id) is None:
            raise HTTPException(status_code=404, detail="unknown session")
        if not claude_transcripts.delete_transcript(session_id):
            raise HTTPException(status_code=500, detail="could not delete the transcript file")
    return {"deleted": session_id}


def _project_item(project: claude_projects.ClaudeProject) -> dict:
    return {
        "path": project.path,
        "name": project.name,
        "trust_accepted": project.trust_accepted,
        "last_session_id": project.last_session_id,
        "last_version": project.last_version,
        "last_cost": project.last_cost,
        "last_start_time": _iso(project.last_start_time),
        "last_duration_ms": project.last_duration_ms,
        "lines_added": project.lines_added,
        "lines_removed": project.lines_removed,
        "mcp_servers": project.mcp_servers,
    }


@app.get("/api/projects")
def get_projects() -> dict:
    return {"projects": [_project_item(p) for p in claude_projects.load_projects()]}


@app.delete("/api/projects")
def delete_project(path: str) -> dict:
    # Only a path the snapshot already knows is acted on, matched exactly - the
    # delete below removes a directory tree, so it never runs on arbitrary input.
    if path not in {p.path for p in claude_projects.load_projects()}:
        raise HTTPException(status_code=404, detail="unknown project")
    with _refresh_lock:
        claude_projects.delete_project(path)
        removed = claude_transcripts.delete_project_transcripts(path)
    return {"deleted": path, "transcript_folders_removed": removed}


@app.get("/api/overview")
def get_overview(
    range_: Annotated[str, Query(alias="range")] = "All time",
) -> dict:
    if range_ not in overview_stats.TIME_RANGES:
        raise HTTPException(status_code=422, detail=f"unknown range: {range_!r}")
    return overview_stats.overview(claude_transcripts.load_transcripts(), range_)
