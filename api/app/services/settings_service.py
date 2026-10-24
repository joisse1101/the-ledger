"""Dashboard settings: the worktree-folder list, and applying a saved list to both stores at once."""

from __future__ import annotations

from app import refresh
from app.core.worktrees import BUILT_IN_FOLDER, WorktreeFolder, normalize_folder
from app.repositories import settings_store
from app.repositories.db import history, snapshot
from app.services.errors import InvalidInput


def get_worktree_folders() -> list[WorktreeFolder]:
    """The built-in folder first, then the user's, in the order they were added."""
    return [WorktreeFolder(BUILT_IN_FOLDER, True)] + [
        WorktreeFolder(folder, False) for folder in settings_store.load_worktree_folders()
    ]


def _validated(raw_folders: list[str]) -> list[str]:
    folders: list[str] = []
    for raw in raw_folders:
        try:
            folder = normalize_folder(raw)
        except ValueError as err:
            raise InvalidInput(f"'{raw}': {err}") from err
        if folder == BUILT_IN_FOLDER or folder in folders:
            raise InvalidInput(f"'{folder}' is already listed.")
        folders.append(folder)
    return folders


def save_worktree_folders(raw_folders: list[str]) -> list[WorktreeFolder]:
    """Replace the user's folders, then bring history and the snapshot in line before returning.

    History is reconciled before the rescan, so the rescan's live rows land on reconciled history.
    Both run under the refresh lock, so the timer's rescan can't interleave with a half-applied save.
    """
    folders = _validated(raw_folders)
    with refresh.lock:
        settings_store.save_worktree_folders(folders)
        history.correct_worktree_rows()
        snapshot.refresh()
    return get_worktree_folders()
