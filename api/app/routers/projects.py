"""The projects list and project deletion."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.security import is_local
from app.schemas.projects import project_item, project_repo_item
from app.services import project_repo_service, project_service

router = APIRouter()


@router.get("/api/projects")
def get_projects() -> dict:
    return {"projects": [project_item(p) for p in project_service.list_projects()]}


@router.get("/api/projects/repos")
def get_project_repos() -> dict:
    # No parameters on purpose: the folders git and gh run in are the known projects', never a request's.
    return {"repos": [project_repo_item(r) for r in project_repo_service.list_project_repos()]}


@router.delete("/api/projects")
def delete_project(path: str, request: Request) -> dict:
    # A valid token widens what a remote device can read/trigger, but never authorizes a delete.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
    removed = project_service.delete_project(path)
    return {"deleted": path, "transcript_folders_removed": removed}
