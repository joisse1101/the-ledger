"""The projects list and project deletion."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app import refresh
from app.core.security import is_local
from app.repositories import claude_projects, claude_transcripts
from app.schemas.projects import project_item

router = APIRouter()


@router.get("/api/projects")
def get_projects() -> dict:
    return {"projects": [project_item(p) for p in claude_projects.load_projects()]}


@router.delete("/api/projects")
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
