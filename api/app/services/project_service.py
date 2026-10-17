"""Projects: the list and deleting one with its transcripts."""

from __future__ import annotations

from app import refresh
from app.repositories import claude_projects, claude_transcripts
from app.services.errors import NotFound


def list_projects() -> list[claude_projects.ClaudeProject]:
    return claude_projects.load_projects()


def delete_project(path: str) -> int:
    """Delete a project the snapshot knows; returns how many transcript folders were removed."""
    # Only a path the snapshot already knows is acted on, matched exactly - the
    # delete below removes a directory tree, so it never runs on arbitrary input.
    if path not in {p.path for p in claude_projects.load_projects()}:
        raise NotFound("unknown project")
    with refresh.lock:
        claude_projects.delete_project(path)
        return claude_transcripts.delete_project_transcripts(path)
