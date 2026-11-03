"""Opens a folder in the machine's file manager. The opener is an argument, so tests pass a fake
and no real window opens."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable


def open_in_file_manager(path: str) -> None:
    """The real opener: Windows Explorer. Raises OSError when it cannot be started."""
    os.startfile(path)  # type: ignore[attr-defined]  # Windows only, as is the rest of this app


def open_folder(folder: Path, opener: Callable[[str], None]) -> None:
    """Create `folder` if it is missing, then hand it to `opener`. OSError propagates."""
    folder.mkdir(parents=True, exist_ok=True)
    opener(str(folder))
