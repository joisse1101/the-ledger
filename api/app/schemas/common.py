"""Types and helpers every schema module shares."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Path

def iso(value) -> Optional[str]:
    return value.isoformat() if value else None


# Real session IDs are UUIDs. Anything else never reaches a path or a query.
SESSION_ID_PATTERN = r"^[A-Za-z0-9-]{1,64}$"
SessionId = Annotated[str, Path(pattern=SESSION_ID_PATTERN)]
