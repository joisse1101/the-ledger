"""FastAPI server for the dashboard: a JSON API over the claude_* data modules."""

from __future__ import annotations

import argparse
import asyncio
import logging
import mimetypes
import os
import threading
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path as FilePath
from typing import Annotated, Literal, Mapping, Optional, Sequence

import uvicorn
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse
from starlette.middleware.gzip import GZipMiddleware

import banner
import claude_context
import claude_db
import claude_projects
import claude_transcripts
import overview_stats
import transcript_query
from live_snapshot import LiveSnapshot
from security import TOKEN_ENV, SecurityMiddleware, provision_token

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

# Set by main() when the server is reachable from other devices (or LEDGER_TOKEN is
# set). While None, no token exists, so every request that isn't plain local is refused.
access_token: Optional[str] = None

app.add_middleware(GZipMiddleware, minimum_size=1024)
# Added last so it is outermost: nothing else runs for a refused request.
app.add_middleware(SecurityMiddleware, token=lambda: access_token)


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


# ---------------------------------------------------------------- front end

WEB_DIST = FilePath(__file__).resolve().parent / "web" / "dist"

# Windows takes these from the registry and can answer text/plain for .js, which
# browsers refuse to run as a module script.
for _suffix, _type in (
    (".js", "text/javascript"),
    (".mjs", "text/javascript"),
    (".css", "text/css"),
    (".svg", "image/svg+xml"),
    (".json", "application/json"),
    (".webmanifest", "application/manifest+json"),
):
    mimetypes.add_type(_type, _suffix)


def frontend_built() -> bool:
    return (WEB_DIST / "index.html").is_file()


def _dist_file(path: str) -> Optional[FilePath]:
    """The file under web/dist that `path` names, or None. Never anything outside it."""
    root = WEB_DIST.resolve()
    try:
        candidate = (root / path).resolve()
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() and candidate.is_relative_to(root) else None


# Registered after every API route, so it only sees what they didn't match. It takes
# every method so that an unknown /api path is a 404 whatever the verb.
@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
def frontend(path: str, request: Request):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404)  # JSON 404, never the page
    if request.method != "GET":
        raise HTTPException(status_code=405, headers={"Allow": "GET"})
    if not frontend_built():
        return PlainTextResponse(banner.NOT_BUILT_MESSAGE, status_code=503)
    asset = _dist_file(path)
    if asset is not None:
        # Vite names what it puts in assets/ by content hash, so those never change.
        immutable = path.startswith("assets/")
        return FileResponse(
            asset,
            headers={"Cache-Control": "public, max-age=31536000, immutable" if immutable else "no-cache"},
        )
    if "." in path.rsplit("/", 1)[-1]:
        raise HTTPException(status_code=404)  # a file that isn't there, not a page route
    return FileResponse(WEB_DIST / "index.html", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------- command line

DEFAULT_HOST = "127.0.0.1"
LAN_HOST = "0.0.0.0"
DEFAULT_PORT = 8501
_LOOPBACK_BINDS = frozenset({"127.0.0.1", "localhost", "::1"})
_WILDCARD_BINDS = frozenset({"0.0.0.0", "::", ""})


@dataclass(frozen=True)
class Settings:
    host: str
    port: int

    @property
    def exposed(self) -> bool:
        """Whether devices other than this machine can connect."""
        return self.host not in _LOOPBACK_BINDS


def parse_settings(
    argv: Optional[Sequence[str]] = None, environ: Mapping[str, str] = os.environ
) -> Settings:
    """--host beats --lan beats LEDGER_HOST beats 127.0.0.1; --port beats LEDGER_PORT beats 8501."""
    parser = argparse.ArgumentParser(
        prog="python server.py",
        description="The Ledger: a dashboard for your Claude Code sessions.",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help=f"serve other devices on the network (binds {LAN_HOST}); they need the access token",
    )
    parser.add_argument("--host", help=f"address to bind (default {DEFAULT_HOST}, env LEDGER_HOST)")
    parser.add_argument("--port", type=int, help=f"port to serve on (default {DEFAULT_PORT}, env LEDGER_PORT)")
    args = parser.parse_args(argv)

    host = args.host or (LAN_HOST if args.lan else None) or environ.get("LEDGER_HOST") or DEFAULT_HOST
    if args.port is not None:
        port = args.port
    elif environ.get("LEDGER_PORT", "").strip():
        try:
            port = int(environ["LEDGER_PORT"])
        except ValueError:
            parser.error(f"LEDGER_PORT must be a number, got {environ['LEDGER_PORT']!r}")
    else:
        port = DEFAULT_PORT
    if not 1 <= port <= 65535:
        parser.error(f"port must be between 1 and 65535, got {port}")
    return Settings(host=host, port=port)


def main(argv: Optional[Sequence[str]] = None) -> None:
    global access_token
    settings = parse_settings(argv)

    # A token exists whenever other devices can connect, or when the user set one
    # (so a tunnel on this machine can be let in with it).
    if settings.exposed or os.environ.get(TOKEN_ENV, "").strip():
        access_token = provision_token()

    lan_addresses = qr = None
    if settings.exposed:
        lan_addresses = (
            banner.discover_ipv4() if settings.host in _WILDCARD_BINDS else [settings.host]
        )
        if lan_addresses:
            qr = banner.render_qr(f"http://{lan_addresses[0]}:{settings.port}/?token={access_token}")
    print(
        banner.build_banner(
            port=settings.port,
            frontend_built=frontend_built(),
            lan_addresses=lan_addresses,
            token=access_token,
            qr=qr,
        ),
        flush=True,
    )

    # No access log: it would write every ?token=... URL to the terminal. proxy_headers off:
    # the peer address must stay the real one, not whatever a header claims.
    uvicorn.run(app, host=settings.host, port=settings.port, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
