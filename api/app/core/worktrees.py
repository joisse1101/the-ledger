"""Claude Code worktrees: recognising one from a session's working directory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# The first `/.claude/worktrees/` keeps the repo root as the shortest prefix.
_WORKTREE_PATH = re.compile(r"^(?P<repo>.+?)/\.claude/worktrees/(?P<name>[^/]+)(?:/|$)")


@dataclass(frozen=True)
class Worktree:
    repo_root: str
    name: str


def parse_worktree(cwd: str) -> Optional[Worktree]:
    """The worktree `cwd` is inside, or None when it is not under `<repo>/.claude/worktrees/<name>`."""
    match = _WORKTREE_PATH.match(cwd.replace("\\", "/"))
    if match is None:
        return None
    return Worktree(repo_root=match["repo"], name=match["name"])
