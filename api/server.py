"""FastAPI server for the dashboard: a JSON API over the claude_* data modules."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import pathlib
import subprocess
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, Mapping, Optional, Sequence
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, HTTPException, Path, Query, Request
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware

import banner
import claude_context
import claude_db
import claude_projects
import claude_transcripts
import overview_stats
import transcript_query
from live_snapshot import LiveSnapshot
from pending_decisions import PendingDecisions
from security import SecurityMiddleware, is_local, provision_token

log = logging.getLogger("ledger")

# The background rescan runs every 10 minutes for as long as the server is up.
REFRESH_INTERVAL_SECONDS = 10 * 60

# refresh() rewrites both tables and can take seconds on a big history, so it is
# serialised process-wide: startup, the timer and POST /api/refresh never overlap.
_refresh_lock = threading.Lock()

# The one place the live registry is read from; see LiveSnapshot.
live = LiveSnapshot()

# In-memory pending tool-permission decisions relayed from live sessions; see pending_decisions.py.
decisions = PendingDecisions()

# Invoked, unmodified, by POST /api/sessions/{id}/open-repo - this repo's own copy, not any
# installed-under-%USERPROFILE% one, so opening a repo window needs no separate install step.
OPEN_REPO_SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "Open-ClaudeRepoWindow.ps1"


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
    # Normally already set by main() before this process's own uvicorn.run() call, so this is a
    # no-op then. --reload's subprocess is the exception: uvicorn imports "server:app" fresh in a
    # separate process that never runs main() at all, so this is that process's only chance to
    # provision the token it actually serves with (re-reads the same stored file main() already
    # wrote, so it's the same token either way).
    global access_token
    if access_token is None:
        access_token = provision_token()

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

# Set by main() on every start. While None (tests that never call main()), no token
# exists, so every request that isn't plain local is refused.
access_token: Optional[str] = None

DEFAULT_FRONTEND_PORT = 4173  # Vite's own `vite preview` default

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityMiddleware, token=lambda: access_token)


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


@app.get("/api/meta")
def get_meta(request: Request) -> dict:
    return {"refreshed_at": _iso(claude_db.refreshed_at()), "is_local": is_local(request)}


@app.post("/api/refresh")
def post_refresh() -> dict:
    return {"refreshed_at": _iso(locked_refresh())}


@app.get("/api/live")
def get_live() -> dict:
    return {
        "sessions": [
            {**item, "pending_decision": decisions.peek(item["session_id"])} for item in live.get()
        ]
    }


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
def delete_session(session_id: SessionId, request: Request) -> dict:
    # A valid token widens what a remote device can read/trigger, but never authorizes a delete.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
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


class DecisionRequest(BaseModel):
    tool_name: str
    tool_input: dict


class DecisionAnswer(BaseModel):
    decision: Literal["allow", "deny"]
    reason: Optional[str] = None


@app.post("/api/sessions/{session_id}/decisions")
async def post_decision(session_id: SessionId, body: DecisionRequest) -> dict:
    """Called by the relay hook only. Registers/waits on a pending decision when this session's
    control view is being watched, else replies "no opinion" immediately - see pending_decisions.py."""
    return await decisions.request_decision(session_id, body.tool_name, body.tool_input)


@app.get("/api/sessions/{session_id}/pending-decision")
def get_pending_decision(session_id: SessionId) -> dict:
    # The poll itself is the heartbeat that keeps this session "watched" for the relay hook's gate.
    decisions.touch_watch(session_id)
    return {"pending_decision": decisions.peek(session_id)}


@app.post("/api/sessions/{session_id}/decisions/answer")
async def post_decision_answer(session_id: SessionId, body: DecisionAnswer) -> dict:
    # async, like post_decision: answer() resolves an asyncio.Event that post_decision awaits on
    # this same event-loop thread, and asyncio.Event isn't safe to set() from another thread (a
    # plain `def` route runs in Starlette's threadpool instead) - the timeout would still mask a
    # correctness bug here, but only after a very unresponsive delay.
    if not decisions.answer(session_id, body.decision, body.reason):
        raise HTTPException(status_code=409, detail="no pending decision for this session")
    return {"answered": session_id}


@app.post("/api/sessions/{session_id}/open-repo")
def post_open_repo(session_id: SessionId) -> dict:
    # The registry's own cwd, never a request parameter - the same rule GET /api/sessions/{id} follows.
    cwd = live.cwd_for(session_id)
    if cwd is None:
        raise HTTPException(status_code=404, detail="unknown or not-live session")
    uri = f"claudecode://open?path={quote(cwd, safe='')}"
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPEN_REPO_SCRIPT), uri],
        check=False,
    )
    return {"opened": session_id}


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
def delete_project(path: str, request: Request) -> dict:
    # A valid token widens what a remote device can read/trigger, but never authorizes a delete.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
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


# ---------------------------------------------------------------- command line

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8501
_LOOPBACK_BINDS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    frontend_port: int
    reload: bool = False

    @property
    def exposed(self) -> bool:
        """Whether devices other than this machine can connect."""
        return self.host not in _LOOPBACK_BINDS


def _parse_port(value: Optional[int], env_name: str, environ: Mapping[str, str], default: int, parser) -> int:
    port = default
    if value is not None:
        port = value
    elif environ.get(env_name, "").strip():
        try:
            port = int(environ[env_name])
        except ValueError:
            parser.error(f"{env_name} must be a number, got {environ[env_name]!r}")
    if port not in range(1, 65536):
        parser.error(f"port must be between 1 and 65535, got {port}")
    return port


def parse_settings(
    argv: Optional[Sequence[str]] = None, environ: Mapping[str, str] = os.environ
) -> Settings:
    """--host beats LEDGER_HOST beats 127.0.0.1; --port beats LEDGER_PORT beats 8501;
    --frontend-port beats LEDGER_FRONTEND_PORT beats 4173 (only used for the printed link — this
    process never connects to the frontend's port itself). `--lan` is no longer a bind mode: other
    devices now reach the app through the containerized gateway (see CLAUDE.md), so passing it exits
    with an error rather than doing anything. `--reload` has no env var (dev-only, always explicit)."""
    parser = argparse.ArgumentParser(
        prog="python server.py",
        description="The Ledger: a dashboard for your Claude Code sessions.",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="removed - start the containerized gateway instead (see CLAUDE.md's Setup & Run)",
    )
    parser.add_argument("--host", help=f"address to bind (default {DEFAULT_HOST}, env LEDGER_HOST)")
    parser.add_argument("--port", type=int, help=f"port to serve on (default {DEFAULT_PORT}, env LEDGER_PORT)")
    parser.add_argument(
        "--frontend-port",
        type=int,
        help=f"port the frontend is served on (default {DEFAULT_FRONTEND_PORT}, env LEDGER_FRONTEND_PORT)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="restart on code changes (dev only - imports the app fresh per restart, so this "
        "process's own startup banner/token print reflects only the very first start)",
    )
    args = parser.parse_args(argv)

    if args.lan:
        parser.error(
            "--lan has been removed: other devices connect through the containerized gateway now "
            "(see CLAUDE.md's Setup & Run), not a backend bind mode."
        )

    host = args.host or environ.get("LEDGER_HOST") or DEFAULT_HOST
    port = _parse_port(args.port, "LEDGER_PORT", environ, DEFAULT_PORT, parser)
    frontend_port = _parse_port(
        args.frontend_port, "LEDGER_FRONTEND_PORT", environ, DEFAULT_FRONTEND_PORT, parser
    )
    return Settings(host=host, port=port, frontend_port=frontend_port, reload=args.reload)


def main(argv: Optional[Sequence[str]] = None) -> None:
    global access_token
    settings = parse_settings(argv)

    # Provisioned unconditionally: the gateway (a separate process) is what decides whether
    # anyone off this machine can ever present it, so the backend no longer gates this on
    # its own bind address.
    access_token = provision_token()

    print(banner.build_banner(frontend_port=settings.frontend_port), flush=True)

    # No access log: it would write every ?token=... URL to the terminal. proxy_headers off:
    # the peer address must stay the real one, not whatever a header claims.
    if settings.reload:
        # reload=True only takes effect when the app is passed as an import string - uvicorn
        # watches the cwd, and on each change spawns a fresh subprocess that imports "server:app"
        # itself (this process's own `app` object above is never reused); see lifespan() for how
        # that subprocess still gets a token.
        uvicorn.run(
            "server:app",
            host=settings.host,
            port=settings.port,
            reload=True,
            access_log=False,
            proxy_headers=False,
        )
    else:
        uvicorn.run(app, host=settings.host, port=settings.port, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
