"""The JSON shape of the settings, and the body that saves them."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.core.worktrees import WorktreeFolder


class WidgetSettingsRequest(BaseModel):
    # Left unchecked here: the service validates it, so a bad value answers with a readable reason
    # rather than a schema error.
    max_projects: Optional[object] = None


class SettingsRequest(BaseModel):
    # Each part is optional, and a part that is left out stays as it was.
    # The user's folders only; the built-in one is always included and never sent.
    worktree_folders: Optional[list[str]] = Field(default=None, max_length=100)
    widget: Optional[WidgetSettingsRequest] = None


def settings_body(folders: list[WorktreeFolder], max_projects: int) -> dict:
    return {
        "worktree_folders": [{"path": f.path, "built_in": f.built_in} for f in folders],
        "widget": {"max_projects": max_projects},
    }
