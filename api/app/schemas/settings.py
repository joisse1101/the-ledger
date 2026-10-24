"""The JSON shape of the settings, and the body that saves them."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.worktrees import WorktreeFolder


class SettingsRequest(BaseModel):
    # The user's folders only; the built-in one is always included and never sent.
    worktree_folders: list[str] = Field(max_length=100)


def settings_body(folders: list[WorktreeFolder]) -> dict:
    return {"worktree_folders": [{"path": f.path, "built_in": f.built_in} for f in folders]}
