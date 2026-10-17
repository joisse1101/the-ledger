"""The Files page: the drop folder, available only while Remote mode is on."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.core.security import is_local
from app.schemas.files import file_json
from app.services import file_service

router = APIRouter()
require_file_drop = Depends(file_service.require_enabled)


@router.get("/api/files", dependencies=[require_file_drop])
def get_files() -> dict:
    return {"files": [file_json(entry) for entry in file_service.list_files()]}


@router.put("/api/files", dependencies=[require_file_drop])
async def put_file(request: Request, name: Annotated[str, Query(min_length=1)]) -> dict:
    return file_json(await file_service.save_file(name, request.stream()))


@router.get("/api/files/{name}", dependencies=[require_file_drop])
def get_file(name: str) -> FileResponse:
    return FileResponse(file_service.download_path(name), filename=name)


@router.post("/api/files/{name}/download-link", dependencies=[require_file_drop])
def post_download_link(name: str) -> dict:
    return {"url": file_service.issue_download_link(name)}


@router.get("/api/files/download/{ticket}", dependencies=[require_file_drop])
def get_download(ticket: str) -> FileResponse:
    # Reachable without the bearer token (see security.py): the ticket is the credential.
    name, path = file_service.redeem_download(ticket)
    return FileResponse(path, filename=name, headers={"Cache-Control": "no-store"})


@router.delete("/api/files/{name}", dependencies=[require_file_drop])
def delete_file(name: str, request: Request) -> dict:
    # Like the session and project deletes: a valid token never authorizes removing files.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="delete requires a local request")
    file_service.delete_file(name)
    return {"deleted": name}
