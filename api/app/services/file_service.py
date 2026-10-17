"""The drop folder: listing, saving, downloading and deleting files, available only in Remote mode."""

from __future__ import annotations

import errno
import logging
import os
import pathlib
from typing import AsyncIterable

from app import deps
from app.infra import file_drop
from app.services.errors import Forbidden, NotFound, StorageFull

log = logging.getLogger("ledger")


def require_enabled() -> None:
    """The Files feature exists only while Remote mode is on, for the PC's own browser too."""
    if not deps.decisions.remote_mode_enabled():
        raise Forbidden("Remote mode is off")


def _drop_file(name: str) -> pathlib.Path:
    try:
        return file_drop.resolve_existing(file_drop.drop_dir(os.environ), name)
    except file_drop.FileDropError as err:
        raise NotFound(str(err)) from err


def list_files() -> list[file_drop.FileEntry]:
    return file_drop.list_files(file_drop.drop_dir(os.environ))


async def save_file(name: str, chunks: AsyncIterable[bytes]) -> file_drop.FileEntry:
    try:
        entry = await file_drop.save_async_stream(file_drop.drop_dir(os.environ), name, chunks)
    except OSError as err:
        if err.errno != errno.ENOSPC:
            raise
        log.warning("file_drop op=upload name=%s result=disk_full", name)
        raise StorageFull("not enough disk space for this file") from err
    log.info("file_drop op=upload name=%s size=%d", entry.name, entry.size)
    return entry


def download_path(name: str) -> pathlib.Path:
    path = _drop_file(name)
    log.info("file_drop op=download name=%s", name)
    return path


def issue_download_link(name: str) -> str:
    _drop_file(name)  # 404 for a file that isn't there, before a ticket is spent on it
    return f"/api/files/download/{deps.download_tickets.issue(name)}"


def redeem_download(ticket: str) -> tuple[str, pathlib.Path]:
    """The file name and path a single-use ticket stands for."""
    name = deps.download_tickets.redeem(ticket)
    if name is None:
        raise Forbidden("this download link is invalid or has expired")
    return name, download_path(name)


def delete_file(name: str) -> None:
    _drop_file(name).unlink()
    log.info("file_drop op=delete name=%s", name)
