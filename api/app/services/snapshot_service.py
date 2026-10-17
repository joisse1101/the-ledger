"""The SQLite snapshot's freshness and the manual rescan."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app import refresh
from app.repositories.db import snapshot


def refreshed_at() -> Optional[datetime]:
    return snapshot.refreshed_at()


def rescan() -> datetime:
    return refresh.locked_refresh()
