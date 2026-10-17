"""The Files page: the drop folder, available only while Remote mode is on."""

from __future__ import annotations

import errno
import logging
import os
import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app import deps
from app.core.security import is_local
from app.infra import file_drop
from app.schemas.files import file_json

log = logging.getLogger("ledger")

router = APIRouter()


def _require_file_drop() -> None:
    """The Files feature exists only while Remote mode is on, for the PC's own browser too."""
    if not deps.decisions.remote_mode_enabled():
        raise HTTPException(status_code=403, detail="Remote mode is off")


def _drop_file(name: str) -> pathlib.Path:
    try:
        return file_drop.resolve_existing(file_drop.drop_dir(os.environ), name)
    except file_drop.FileDropError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@router.get("/api/files", dependencies=[Depends(_require_file_drop)])
def get_files() -> dict:
    return {"files": [file_json(entry) for entry in file_drop.list_files(file_drop.drop_dir(os.environ))]}


@router.put("/api/files", dependencies=[Depends(_require_file_drop)])
async def put_file(request: Request, name: Annotated[str, Query(min_length=1)]) -> dict:
    try:
        entry = await file_drop.save_async_stream(file_drop.drop_dir(os.environ), name, request.stream())
    except OSError as err:
        if err.errno != errno.ENOSPC:
            raise
        log.warning("file_drop op=upload name=%s result=disk_full", name)
        raise HTTPException(status_code=507, detail="not enough disk space for this file") from err
    log.info("file_drop op=upload name=%s size=%d", entry.name, entry.size)
    return file_json(entry)


@router.get("/api/files/{name}", dependencies=[Depends(_require_file_drop)])
def get_file(name: str) -> FileResponse:
    path = _drop_file(name)
    log.info("file_drop op=download name=%s", name)
    return FileResponse(path, filename=name)


@router.post("/api/files/{name}/download-link", dependencies=[Depends(_require_file_drop)])
def post_download_link(name: str) -> dict:
    _drop_file(name)  # 404 for a file that isn't there, before a ticket is spent on it
    return {"url": f"/api/files/download/{deps.download_tickets.issue(name)}"}


@router.get("/api/files/download/{ticket}", dependencies=[Depends(_require_file_drop)])
def get_download(ticket: str) -> FileResponse:
    # Reachable without the bearer token (see security.py): the ticket is the credential.
    name = deps.download_tickets.redeem(ticket)
    if name is None:
        raise HTTPException(status_code=403, detail="this download link is invalid or has expired")
    path = _drop_file(name)
    log.info("file_drop op=download name=%s", name)
    return FileResponse(path, filename=name, headers={"Cache-Control": "no-store"})


@router.delete("/api/files/{name}", dependencies=[Depends(_require_file_drop)])
def delete_file(name: str, request: Request) -> dict:
    # Like the session and project deletes: a valid token never authorizes removing files.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
    _drop_file(name).unlink()
    log.info("file_drop op=delete name=%s", name)
    return {"deleted": name}
