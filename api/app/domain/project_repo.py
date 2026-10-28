"""One project's repo as the Projects page shows it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core import remote_url


@dataclass(frozen=True)
class ProjectRepo:
    path: str
    host: Optional[str]
    url: Optional[str]
    issues: Optional[int]
    prs: Optional[int]

    @property
    def complete(self) -> bool:
        """False when something that should be known is missing, so the entry is retried sooner."""
        if self.url is None:
            return False
        return self.host != remote_url.GITHUB_LABEL or self.issues is not None
