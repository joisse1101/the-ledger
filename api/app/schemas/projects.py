"""The JSON shape of a project row."""

from __future__ import annotations

from app.repositories import claude_projects
from app.schemas.common import iso
from app.domain.project_repo import ProjectRepo


def project_repo_item(repo: ProjectRepo) -> dict:
    return {"path": repo.path, "host": repo.host, "url": repo.url, "issues": repo.issues, "prs": repo.prs}


def project_item(project: claude_projects.ClaudeProject) -> dict:
    return {
        "path": project.path,
        "name": project.name,
        "trust_accepted": project.trust_accepted,
        "last_session_id": project.last_session_id,
        "last_version": project.last_version,
        "last_cost": project.last_cost,
        "last_start_time": iso(project.last_start_time),
        "last_duration_ms": project.last_duration_ms,
        "lines_added": project.lines_added,
        "lines_removed": project.lines_removed,
        "mcp_servers": project.mcp_servers,
    }
