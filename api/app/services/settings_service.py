"""Dashboard settings: the worktree-folder list, and applying a saved list to both stores at once."""

from __future__ import annotations

import logging
from typing import Optional

from app import refresh
from app.core.widget_settings import validate_afk_minutes, validate_break_minutes, validate_max_projects
from app.core.worktrees import BUILT_IN_FOLDER, WorktreeFolder, normalize_folder
from app.repositories import settings_store
from app.repositories.db import history, snapshot
from app.services.errors import InvalidInput, OperationFailed

logger = logging.getLogger(__name__)


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


def get_max_projects() -> int:
    return settings_store.load_max_projects()


def _validated_max_projects(raw: object) -> int:
    try:
        return validate_max_projects(raw)
    except ValueError as err:
        raise InvalidInput(str(err)) from err


def get_afk_minutes() -> int:
    return settings_store.load_afk_minutes()


def _validated_afk_minutes(raw: object) -> int:
    try:
        return validate_afk_minutes(raw)
    except ValueError as err:
        raise InvalidInput(str(err)) from err


def get_break_minutes() -> int:
    return settings_store.load_break_minutes()


def _validated_break_minutes(raw: object) -> int:
    try:
        return validate_break_minutes(raw)
    except ValueError as err:
        raise InvalidInput(str(err)) from err


def _apply_worktree_folders(folders: list[str]) -> None:
    """Replace the user's folders, then bring history and the snapshot in line before returning.

    History is reconciled before the rescan, so the rescan's live rows land on reconciled history.
    Both run under the refresh lock, so the timer's rescan can't interleave with a half-applied save.
    """
    with refresh.lock:
        settings_store.save_worktree_folders(folders)
        history.correct_worktree_rows()
        snapshot.refresh()


def save_settings(
    raw_folders: Optional[list[str]],
    raw_max_projects: Optional[object],
    raw_afk_minutes: Optional[object] = None,
    raw_break_minutes: Optional[object] = None,
) -> None:
    """Save whichever settings were sent; the others stay as they are.

    Everything is validated before anything is saved, so a bad value never leaves a half-applied
    request. The widget's numbers are display preferences: saving them does not touch history or the snapshot.
    """
    folders = None if raw_folders is None else _validated(raw_folders)
    max_projects = None if raw_max_projects is None else _validated_max_projects(raw_max_projects)
    afk_minutes = None if raw_afk_minutes is None else _validated_afk_minutes(raw_afk_minutes)
    break_minutes = None if raw_break_minutes is None else _validated_break_minutes(raw_break_minutes)
    try:
        if max_projects is not None:
            settings_store.save_max_projects(max_projects)
        if afk_minutes is not None:
            settings_store.save_afk_minutes(afk_minutes)
        if break_minutes is not None:
            settings_store.save_break_minutes(break_minutes)
        if folders is not None:
            _apply_worktree_folders(folders)
    except settings_store.SettingsUnreadable as err:
        logger.warning("settings_save_refused error=%s", err)
        raise OperationFailed(f"The settings file can't be read, so nothing was saved. Fix or delete it: {err}") from err
