"""Where each project's repo is hosted and how many issues and pull requests are open there.

Looked up per known project (never per requested path), in parallel, and cached: the lookups run
`git` and the GitHub CLI, which can take seconds."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from app.core import remote_url
from app.domain.project_repo import ProjectRepo
from app.infra.repo_cli import RepoCli
from app.repositories import claude_projects

CACHE_TTL_SECONDS = 300
# A lookup that came back incomplete is retried sooner, so signing in to `gh` shows up quickly
# without a signed-out `gh` being asked again on every poll.
FAILURE_TTL_SECONDS = 60
MAX_WORKERS = 4


class ProjectRepoLookup:
    def __init__(
        self,
        cli: RepoCli,
        clock: Callable[[], float] = time.monotonic,
        ttl: float = CACHE_TTL_SECONDS,
        failure_ttl: float = FAILURE_TTL_SECONDS,
    ) -> None:
        self._cli = cli
        self._clock = clock
        self._ttl = ttl
        self._failure_ttl = failure_ttl
        self._cache: dict[str, tuple[float, ProjectRepo]] = {}
        self._lock = threading.Lock()

    def lookup_all(self, paths: list[str]) -> list[ProjectRepo]:
        """One entry per path, in order. A path that fails to resolve yields an all-None entry."""
        if not paths:
            return []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            return list(pool.map(self._lookup, paths))

    def clear(self) -> None:
        """Forget every cached lookup, so the next call reads git and `gh` again."""
        with self._lock:
            self._cache.clear()

    def _lookup(self, path: str) -> ProjectRepo:
        with self._lock:
            cached = self._cache.get(path)
        if cached is not None and self._clock() < cached[0]:
            return cached[1]
        repo = self._resolve(path)
        expires_at = self._clock() + (self._ttl if repo.complete else self._failure_ttl)
        with self._lock:
            self._cache[path] = (expires_at, repo)
        return repo

    def _resolve(self, path: str) -> ProjectRepo:
        remote = self._cli.remote_url(path)
        url = remote_url.web_url(remote) if remote else None
        if url is None:
            return ProjectRepo(path=path, host=None, url=None, issues=None, prs=None)
        host = remote_url.host_label(url)
        counts = self._cli.open_counts(path) if host == remote_url.GITHUB_LABEL else None
        return ProjectRepo(
            path=path,
            host=host,
            url=url,
            issues=counts.issues if counts else None,
            prs=counts.prs if counts else None,
        )


lookup = ProjectRepoLookup(RepoCli())


def clear_cache() -> None:
    lookup.clear()


def list_project_repos() -> list[ProjectRepo]:
    """Every project Claude Code knows, with its repo info. The paths come from Claude Code's own
    configuration, so a client cannot point the git and `gh` calls at a folder of its choosing."""
    return lookup.lookup_all([project.path for project in claude_projects.load_projects()])
