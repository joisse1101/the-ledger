"""One session's detail, its deletion and opening its repo."""

from __future__ import annotations

import subprocess
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request

from app import deps, refresh
from app.core.security import is_local
from app.domain import claude_context
from app.repositories import claude_db, claude_transcripts
from app.schemas.common import SessionId, iso
from app.schemas.sessions import detail_json

router = APIRouter()

# Invoked, unmodified, by POST /api/sessions/{id}/open-repo - this repo's own copy, not any
# installed-under-%USERPROFILE% one, so opening a repo window needs no separate install step.
OPEN_REPO_SCRIPT = deps.REPO_ROOT / "hooks" / "scripts" / "Open-ClaudeRepoWindow.ps1"


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
            "started_at": iso(transcript.started_at),
            "updated_at": iso(transcript.updated_at),
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


@router.get("/api/sessions/{session_id}")
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
        "detail": detail_json(detail) if detail is not None else None,
    }


@router.delete("/api/sessions/{session_id}")
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


@router.post("/api/sessions/{session_id}/open-repo")
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
