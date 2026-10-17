"""Request bodies for the Remote mode routes."""

from __future__ import annotations

from pydantic import BaseModel

class RemoteModeRequest(BaseModel):
    enabled: bool
