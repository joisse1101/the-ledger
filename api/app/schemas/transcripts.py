"""The JSON shape of a transcript row in the sessions list."""

from __future__ import annotations

from app.repositories import claude_transcripts
from app.schemas.common import iso

def transcript_item(transcript: claude_transcripts.ClaudeTranscript, live_ids: set[str]) -> dict:
    return {
        "session_id": transcript.session_id,
        "project": transcript.project,
        "title": transcript.title,
        "started_at": iso(transcript.started_at),
        "updated_at": iso(transcript.updated_at),
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
