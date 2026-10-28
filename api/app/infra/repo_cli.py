"""Reads a project folder's git remote and its open issue and pull request counts by running `git`
and the GitHub CLI. Every call goes through the injected `run`, so tests use a fake. A failure
(missing binary, signed-out `gh`, timeout, odd output) is logged and answered with None: the
caller shows `--` rather than failing."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

GIT_TIMEOUT_SECONDS = 10
GH_TIMEOUT_SECONDS = 20
# `gh` lists 30 items unless told otherwise; a repo past this many open items shows this many.
LIST_LIMIT = 1000
# No console window for anything this backend launches on the user's behalf.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass(frozen=True)
class OpenCounts:
    issues: int
    prs: int


class RepoCli:
    def __init__(self, run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> None:
        self._run = run

    def remote_url(self, project_path: str) -> Optional[str]:
        """The `origin` remote's URL, or None when the folder is not a repo or has no origin."""
        result = self._execute(["git", "-C", project_path, "remote", "get-url", "origin"], project_path, GIT_TIMEOUT_SECONDS)
        if result is None:
            return None
        return result.stdout.strip() or None

    def open_counts(self, project_path: str) -> Optional[OpenCounts]:
        """Open issues and open pull requests of the repo `project_path` is a clone of, or None when
        either count cannot be read (so a half-answer is never shown)."""
        issues = self._open_count("issue", project_path)
        prs = self._open_count("pr", project_path)
        if issues is None or prs is None:
            return None
        return OpenCounts(issues=issues, prs=prs)

    def _open_count(self, kind: str, project_path: str) -> Optional[int]:
        command = ["gh", kind, "list", "--state", "open", "--json", "number", "--limit", str(LIST_LIMIT)]
        result = self._execute(command, project_path, GH_TIMEOUT_SECONDS, cwd=Path(project_path))
        if result is None:
            return None
        try:
            items = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning("repo_cli unreadable output command=%s path=%s", command[:3], project_path)
            return None
        return len(items) if isinstance(items, list) else None

    def _execute(
        self, command: list[str], project_path: str, timeout: int, cwd: Optional[Path] = None
    ) -> Optional[Any]:
        try:
            result = self._run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired) as err:
            logger.warning("repo_cli failed command=%s path=%s error=%s", command[:3], project_path, err)
            return None
        if result.returncode != 0:
            logger.warning(
                "repo_cli nonzero exit command=%s path=%s code=%s stderr=%s",
                command[:3],
                project_path,
                result.returncode,
                (result.stderr or "").strip()[:200],
            )
            return None
        return result
