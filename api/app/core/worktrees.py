"""Worktrees: recognising one from a session's working directory."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional

# Claude Code's own worktree folder, always recognised on top of the configured ones.
BUILT_IN_FOLDER = ".claude/worktrees"

_DRIVE_LETTER = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class Worktree:
    repo_root: str
    name: str
    folder: str = BUILT_IN_FOLDER


@dataclass(frozen=True)
class WorktreeFolder:
    """One entry of the configured worktree-folder list."""

    path: str
    built_in: bool


@lru_cache(maxsize=32)
def _worktree_path(folders: tuple[str, ...]) -> re.Pattern[str]:
    # Longest first, so `wt/inner` wins over `wt`; the lazy repo group keeps the outermost repo.
    ordered = sorted({BUILT_IN_FOLDER, *folders}, key=len, reverse=True)
    alternation = "|".join(re.escape(folder) for folder in ordered)
    return re.compile(rf"^(?P<repo>.+?)/(?P<folder>{alternation})/(?P<name>[^/]+)(?:/|$)")


def parse_worktree(cwd: str, folders: Iterable[str] = ()) -> Optional[Worktree]:
    """The worktree `cwd` is inside, or None when it is not under `<repo>/<folder>/<name>`.

    `folders` are the user's normalised worktree folders; the built-in one always applies.
    """
    match = _worktree_path(tuple(folders)).match(cwd.replace("\\", "/"))
    if match is None:
        return None
    return Worktree(repo_root=match["repo"], name=match["name"], folder=match["folder"])


def normalize_folder(raw: str) -> str:
    """`raw` as a stored worktree folder (`/`-separated, no outer slashes); ValueError says why not."""
    if _DRIVE_LETTER.match(raw.strip()) or raw.strip().startswith(("/", "\\")):
        raise ValueError("Must be a path inside the repo, not an absolute path.")
    folder = raw.strip().replace("\\", "/").strip("/")
    if not folder:
        raise ValueError("Enter a folder path.")
    segments = folder.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise ValueError("Must be a path inside the repo, with no '.' or '..' parts.")
    return folder
