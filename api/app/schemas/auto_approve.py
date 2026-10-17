"""Request body for the auto-approve route."""

from __future__ import annotations

from pydantic import BaseModel


class AutoApproveRequest(BaseModel):
    enabled: bool
