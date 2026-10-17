"""FastAPI server for the dashboard: a JSON API over the claude_* data modules."""

from __future__ import annotations

import asyncio
import errno
import logging
import os
import pathlib
import subprocess
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Any, Literal, Optional, Sequence, Union
from urllib.parse import quote

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware

from app import deps, refresh
from app.core.config import parse_settings
from app.infra import banner
from app.infra import file_drop
from app.domain import claude_context
from app.repositories import claude_db
from app.repositories import claude_projects
from app.repositories import claude_transcripts
from app.domain import overview_stats
from app.domain import transcript_query
import gateway_signin
from app.core.security import SecurityMiddleware, is_local, provision_token

log = logging.getLogger("ledger")

REPO_ROOT = deps.REPO_ROOT

# Invoked, unmodified, by POST /api/sessions/{id}/open-repo - this repo's own copy, not any
# installed-under-%USERPROFILE% one, so opening a repo window needs no separate install step.
OPEN_REPO_SCRIPT = REPO_ROOT / "hooks" / "scripts" / "Open-ClaudeRepoWindow.ps1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Normally already set by main() before this process's own uvicorn.run() call, so this is a
    # no-op then. --reload's subprocess is the exception: uvicorn imports "server:app" fresh in a
    # separate process that never runs main() at all, so this is that process's only chance to
    # provision the token it actually serves with (re-reads the same stored file main() already
    # wrote, so it's the same token either way).
    if deps.access_token is None:
        deps.access_token = provision_token()

    if deps.remote is None:
        env_settings = parse_settings([])
        deps.remote = deps.make_remote(env_settings.port, env_settings.frontend_port)
    # Remote mode starts off, so a gateway an earlier backend left running is closed now.
    await asyncio.to_thread(deps.remote.stop_leftovers)

    await asyncio.to_thread(refresh.startup_snapshot)
    task = asyncio.create_task(refresh.refresh_loop())
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

app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SecurityMiddleware, token=lambda: deps.access_token)


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


@app.get("/api/meta")
def get_meta(request: Request) -> dict:
    return {
        "refreshed_at": _iso(claude_db.refreshed_at()),
        "is_local": is_local(request),
        "remote_mode": deps.remote_mode_status(),
    }


class RemoteModeRequest(BaseModel):
    enabled: bool


@app.post("/api/remote-mode")
def post_remote_mode(body: RemoteModeRequest, request: Request) -> dict:
    # Same locality test as the delete routes: a valid token lets another device see and answer
    # prompts while Remote mode is on, but never lets it change Remote mode itself.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="switching Remote mode requires a local request")
    if deps.remote is None:
        raise HTTPException(status_code=503, detail="Remote mode is not available yet")
    if body.enabled:
        deps.remote.start()  # returns at once; clients watch the state in /api/meta
    else:
        deps.remote.stop()
    return deps.remote_mode_status()


@app.get("/api/remote-mode/qr")
def get_remote_mode_qr(request: Request) -> dict:
    # The code contains the access token, so even a valid token isn't enough to read it.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="the sign-in code requires a local request")
    if deps.remote is None or not deps.remote.is_ready():
        raise HTTPException(status_code=409, detail="Remote mode is not ready")
    addresses = banner.discover_ipv4()
    if not addresses or deps.access_token is None:
        raise HTTPException(status_code=409, detail="No network address was found for this machine")
    svg = banner.render_qr_svg(gateway_signin.signin_url(addresses[0], deps.gateway_port, deps.access_token))
    if svg is None:
        raise HTTPException(status_code=503, detail="QR codes are unavailable (the qrcode package is missing)")
    return {
        "svg": svg,
        "display_url": gateway_signin.display_url(addresses[0], deps.gateway_port),
        "expires_at": deps.decisions.remote_mode()["expires_at"],
    }


@app.post("/api/refresh")
def post_refresh() -> dict:
    return {"refreshed_at": _iso(refresh.locked_refresh())}


@app.get("/api/live")
def get_live(request: Request) -> dict:
    deps.sweep_prompts()
    visible = deps.can_see_prompts(request)
    return {
        "sessions": [
            {**item, "pending_decision": deps.decisions.peek(item["session_id"]) if visible else None}
            for item in deps.live.get()
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
        "cost_source": transcript.cost_source,
        "unpriced_models": transcript.unpriced_models,
        "cost_state_flagged": transcript.cost_state_flagged,
        "context": transcript.context,
        "model": transcript.model,
        "used_openspec": transcript.used_openspec,
        "version": transcript.version,
        "git_branch": transcript.git_branch,
        "live": transcript.session_id in live_ids,
    }


SortField = Literal[
    "project", "title", "session_id", "started_at", "updated_at",
    "message_count", "cost", "context", "model", "used_openspec", "version", "git_branch",
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
    live_ids = deps.live.live_ids()
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
            "cost_source": transcript.cost_source,
            "unpriced_models": transcript.unpriced_models,
            "cost_state_flagged": transcript.cost_state_flagged,
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
            "cost_source": None,
            "unpriced_models": [],
            "cost_state_flagged": False,
        }
    else:
        return None
    recap["context"] = context
    recap["avg_tokens_per_message"] = round(context / messages) if context and messages else None
    return recap


def _breakdown_json(breakdown: Optional[claude_context.Breakdown]) -> Optional[dict]:
    if breakdown is None:
        return None
    return {
        "snapshots": [
            {
                "position": snapshot.position,
                "categories": [
                    {
                        "name": category.name,
                        "tokens": category.tokens,
                        "items": [{"label": item.label, "tokens": item.tokens} for item in category.items],
                    }
                    for category in snapshot.categories
                ],
            }
            for snapshot in breakdown.snapshots
        ],
        "turns": [
            {
                "snapshot": row.snapshot,
                "growth": [{"tool": g.tool, "tokens": g.tokens} for g in row.growth],
                "remainder": row.remainder,
            }
            for row in breakdown.turns
        ],
    }


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
        "breakdown": _breakdown_json(detail.breakdown),
    }


@app.get("/api/sessions/{session_id}")
def get_session(session_id: SessionId) -> dict:
    # The working directory is only ever taken from the registry or the snapshot,
    # never from the request, so a client can't point the transcript lookup elsewhere.
    transcript = _find_transcript(session_id)
    live_ids = deps.live.live_ids()
    live_item = next((s for s in deps.live.get() if s["session_id"] == session_id), None)
    cwd = deps.live.cwd_for(session_id) or (transcript.cwd if transcript else None)
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
    if deps.live.is_live_now(session_id):
        raise HTTPException(status_code=409, detail="session is live and cannot be deleted")
    with refresh.lock:  # a concurrent rescan could otherwise re-add the row
        if claude_db.transcript_path_for_session(session_id) is None:
            raise HTTPException(status_code=404, detail="unknown session")
        if not claude_transcripts.delete_transcript(session_id):
            raise HTTPException(status_code=500, detail="could not delete the transcript file")
    return {"deleted": session_id}


class DecisionRequest(BaseModel):
    tool_name: str
    tool_input: dict


@app.post("/api/sessions/{session_id}/decisions")
async def post_decision(session_id: SessionId, body: DecisionRequest, request: Request) -> dict:
    """Called by the relay hook only. Registers the prompt and holds the request until it is
    answered, cleared or the wait elapses - `{decision: null}` then, and the hook prints nothing."""
    # The hook runs on this machine; a remote device has no business registering prompts (a forged
    # one could then be "answered" as if it were real).
    if not is_local(request):
        raise HTTPException(status_code=403, detail="registering a prompt requires a local request")
    return await deps.decisions.request_decision(session_id, body.tool_name, body.tool_input)


@app.get("/api/sessions/{session_id}/pending-decision")
def get_pending_decision(session_id: SessionId, request: Request) -> dict:
    deps.sweep_prompts()
    visible = deps.can_see_prompts(request)
    return {"pending_decision": deps.decisions.peek(session_id) if visible else None}


QUESTION_TOOL = "AskUserQuestion"


class DecisionAnswer(BaseModel):
    decision: Literal["allow", "deny", "answer"]
    reason: Optional[str] = None
    answers: Optional[dict[str, Union[str, list[str]]]] = None


def _checked_answers(prompt: dict[str, Any], answers: dict[str, Union[str, list[str]]]) -> dict[str, Any]:
    """Validate a question's answers against the stored prompt; 422 when they don't fit it.

    Each of the prompt's questions needs exactly one answer keyed by its text: an option label or
    free text ("Other") as a string, or a list only where the question is multi-select.
    """
    asked = {
        q["question"]: bool(q.get("multiSelect"))
        for q in (prompt["tool_input"].get("questions") or [])
        if isinstance(q, dict) and isinstance(q.get("question"), str)
    }
    if not asked:
        raise HTTPException(status_code=422, detail="this prompt has no answerable questions")
    if set(answers) != set(asked):
        raise HTTPException(status_code=422, detail="answers must cover exactly the questions asked")
    for text, value in answers.items():
        if isinstance(value, list):
            if not asked[text]:
                raise HTTPException(status_code=422, detail=f"only a multi-select question takes a list: {text!r}")
            if not value or any(not item.strip() for item in value):
                raise HTTPException(status_code=422, detail=f"pick at least one non-blank option: {text!r}")
        elif not value.strip():
            raise HTTPException(status_code=422, detail=f"answer is blank: {text!r}")
    return {"decision": "answer", "answers": answers}


def _checked_answer(prompt: dict[str, Any], body: DecisionAnswer) -> dict[str, Any]:
    """The answer the hook receives, or a 422 when its shape doesn't fit the kind of prompt."""
    is_question = prompt["tool_name"] == QUESTION_TOOL
    if body.decision == "answer":
        if not is_question:
            raise HTTPException(status_code=422, detail="this is a permission prompt: answer allow or deny")
        if body.answers is None:
            raise HTTPException(status_code=422, detail="answers are required")
        return _checked_answers(prompt, body.answers)
    if is_question:
        raise HTTPException(status_code=422, detail="this is a question: answer with answers")
    if body.decision == "allow":
        return {"decision": "allow"}
    return {"decision": "deny", "reason": (body.reason or "").strip() or None}


@app.post("/api/sessions/{session_id}/decisions/{prompt_id}/answer")
def post_decision_answer(
    session_id: SessionId,
    prompt_id: Annotated[str, Path(pattern=SESSION_ID_PATTERN)],
    body: DecisionAnswer,
    request: Request,
) -> dict:
    # Token and CSRF header were already checked by the middleware; Remote mode is the extra gate
    # for another device.
    if not deps.can_see_prompts(request):
        raise HTTPException(status_code=403, detail="Remote mode is off")
    deps.sweep_prompts()  # a prompt answered in the terminal a moment ago should 409, not "succeed"
    prompt = deps.decisions.get(session_id, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=409, detail="this session already moved on")
    answer = _checked_answer(prompt, body)
    # A plain `def` route runs in Starlette's threadpool; answer() wakes the hook's waiting request
    # on that request's own event loop, so calling it from here is safe.
    if not deps.decisions.answer(session_id, prompt_id, answer):
        raise HTTPException(status_code=409, detail="this session already moved on")
    return {"answered": prompt_id}


@app.post("/api/sessions/{session_id}/open-repo")
def post_open_repo(session_id: SessionId) -> dict:
    # The registry's own cwd, never a request parameter - the same rule GET /api/sessions/{id} follows.
    cwd = deps.live.cwd_for(session_id)
    if cwd is None:
        raise HTTPException(status_code=404, detail="unknown or not-live session")
    uri = f"claudecode://open?path={quote(cwd, safe='')}"
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPEN_REPO_SCRIPT), uri],
        check=False,
    )
    return {"opened": session_id}


def _require_file_drop() -> None:
    """The Files feature exists only while Remote mode is on, for the PC's own browser too."""
    if not deps.decisions.remote_mode_enabled():
        raise HTTPException(status_code=403, detail="Remote mode is off")


def _file_json(entry: file_drop.FileEntry) -> dict:
    return {"name": entry.name, "size": entry.size, "modified": datetime.fromtimestamp(entry.modified).isoformat()}


def _drop_file(name: str) -> pathlib.Path:
    try:
        return file_drop.resolve_existing(file_drop.drop_dir(os.environ), name)
    except file_drop.FileDropError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.get("/api/files", dependencies=[Depends(_require_file_drop)])
def get_files() -> dict:
    return {"files": [_file_json(entry) for entry in file_drop.list_files(file_drop.drop_dir(os.environ))]}


@app.put("/api/files", dependencies=[Depends(_require_file_drop)])
async def put_file(request: Request, name: Annotated[str, Query(min_length=1)]) -> dict:
    try:
        entry = await file_drop.save_async_stream(file_drop.drop_dir(os.environ), name, request.stream())
    except OSError as err:
        if err.errno != errno.ENOSPC:
            raise
        log.warning("file_drop op=upload name=%s result=disk_full", name)
        raise HTTPException(status_code=507, detail="not enough disk space for this file") from err
    log.info("file_drop op=upload name=%s size=%d", entry.name, entry.size)
    return _file_json(entry)


@app.get("/api/files/{name}", dependencies=[Depends(_require_file_drop)])
def get_file(name: str) -> FileResponse:
    path = _drop_file(name)
    log.info("file_drop op=download name=%s", name)
    return FileResponse(path, filename=name)


@app.post("/api/files/{name}/download-link", dependencies=[Depends(_require_file_drop)])
def post_download_link(name: str) -> dict:
    _drop_file(name)  # 404 for a file that isn't there, before a ticket is spent on it
    return {"url": f"/api/files/download/{deps.download_tickets.issue(name)}"}


@app.get("/api/files/download/{ticket}", dependencies=[Depends(_require_file_drop)])
def get_download(ticket: str) -> FileResponse:
    # Reachable without the bearer token (see security.py): the ticket is the credential.
    name = deps.download_tickets.redeem(ticket)
    if name is None:
        raise HTTPException(status_code=403, detail="this download link is invalid or has expired")
    path = _drop_file(name)
    log.info("file_drop op=download name=%s", name)
    return FileResponse(path, filename=name, headers={"Cache-Control": "no-store"})


@app.delete("/api/files/{name}", dependencies=[Depends(_require_file_drop)])
def delete_file(name: str, request: Request) -> dict:
    # Like the session and project deletes: a valid token never authorizes removing files.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
    _drop_file(name).unlink()
    log.info("file_drop op=delete name=%s", name)
    return {"deleted": name}


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
    with refresh.lock:
        claude_projects.delete_project(path)
        removed = claude_transcripts.delete_project_transcripts(path)
    return {"deleted": path, "transcript_folders_removed": removed}


@app.get("/api/overview")
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


def main(argv: Optional[Sequence[str]] = None) -> None:
    settings = parse_settings(argv)

    # Provisioned unconditionally: the gateway (a separate process) is what decides whether
    # anyone off this machine can ever present it, so the backend no longer gates this on
    # its own bind address.
    deps.access_token = provision_token()
    deps.remote = deps.make_remote(settings.port, settings.frontend_port)

    print(banner.build_banner(frontend_port=settings.frontend_port), flush=True)

    # No access log: it would write every ?token=... URL to the terminal. proxy_headers off:
    # the peer address must stay the real one, not whatever a header claims.
    if settings.reload:
        # The reload subprocess builds its own Remote mode lifecycle (see lifespan()); the ports
        # reach it through the same env vars parse_settings reads.
        os.environ["LEDGER_PORT"] = str(settings.port)
        os.environ["LEDGER_FRONTEND_PORT"] = str(settings.frontend_port)
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
