"""One session: look it up, delete it, open its repo."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

from app import deps, refresh
from app.domain import claude_context
from app.repositories import claude_db, claude_transcripts
from app.services.errors import Conflict, NotFound, OperationFailed

# Invoked, unmodified, by POST /api/sessions/{id}/open-repo - this repo's own copy, not any
# installed-under-%USERPROFILE% one, so opening a repo window needs no separate install step.
OPEN_REPO_SCRIPT = deps.REPO_ROOT / "hooks" / "scripts" / "Open-ClaudeRepoWindow.ps1"


@dataclass(frozen=True)
class SessionView:
    session_id: str
    live: bool
    transcript: Optional[claude_transcripts.ClaudeTranscript]
    live_item: Optional[dict]
    detail: Optional[claude_context.SessionDetail]


def _find_transcript(session_id: str) -> Optional[claude_transcripts.ClaudeTranscript]:
    return next((t for t in claude_transcripts.load_transcripts() if t.session_id == session_id), None)


def get_session(session_id: str) -> SessionView:
    # The working directory is only ever taken from the registry or the snapshot,
    # never from the request, so a client can't point the transcript lookup elsewhere.
    transcript = _find_transcript(session_id)
    live_ids = deps.live.live_ids()
    live_item = next((s for s in deps.live.get() if s["session_id"] == session_id), None)
    cwd = deps.live.cwd_for(session_id) or (transcript.cwd if transcript else None)
    if cwd is None:
        raise NotFound("unknown session")
    return SessionView(
        session_id=session_id,
        live=session_id in live_ids,
        transcript=transcript,
        live_item=live_item,
        detail=claude_context.load_detail(session_id, cwd),
    )


def delete_session(session_id: str) -> None:
    # Liveness comes from a fresh registry read: the 1s cached list could still say
    # "not live" for a session that started a moment ago.
    if deps.live.is_live_now(session_id):
        raise Conflict("session is live and cannot be deleted")
    with refresh.lock:  # a concurrent rescan could otherwise re-add the row
        if claude_db.transcript_path_for_session(session_id) is None:
            raise NotFound("unknown session")
        if not claude_transcripts.delete_transcript(session_id):
            raise OperationFailed("could not delete the transcript file")


def open_repo(session_id: str) -> None:
    # The registry's own cwd, never a request parameter - the same rule get_session follows.
    cwd = deps.live.cwd_for(session_id)
    if cwd is None:
        raise NotFound("unknown or not-live session")
    uri = f"claudecode://open?path={quote(cwd, safe='')}"
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(OPEN_REPO_SCRIPT), uri],
        check=False,
    )
