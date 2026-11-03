"""The desktop widget's personal workouts folder: opening it in the file manager."""

from __future__ import annotations

import logging
from typing import Callable

from app import deps
from app.infra import folder_opener
from app.services.errors import OperationFailed

logger = logging.getLogger(__name__)

# The widget builds the same path from its repo root (widget/src/main/config.ts); a test on each side pins it.
PERSONAL_WORKOUTS_FOLDER = "widget/workouts/mine"

# Swapped by tests so no real file manager opens.
opener: Callable[[str], None] = folder_opener.open_in_file_manager


def open_personal_workouts_folder() -> str:
    """Create the personal workouts folder if missing and open it; returns its path.

    Raises OperationFailed, with the path in the message, when the folder cannot be created or opened.
    """
    folder = deps.REPO_ROOT / PERSONAL_WORKOUTS_FOLDER
    try:
        folder_opener.open_folder(folder, opener)
    except OSError as err:
        logger.warning("workouts_open_failed path=%s error=%s", folder, err)
        raise OperationFailed(f"Could not open the folder. Open it by hand: {folder}") from err
    return str(folder)
