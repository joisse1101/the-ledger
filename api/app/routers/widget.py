"""The desktop widget's routes: opening its personal workouts folder, from the local machine only."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.security import is_local
from app.services import widget_service

router = APIRouter()


@router.post("/api/widget/workouts/open")
def post_open_workouts(request: Request) -> dict:
    # A valid token lets another device read the dashboard, never open a folder on this machine.
    if not is_local(request):
        raise HTTPException(status_code=403, detail="opening the workouts folder requires a local request")
    return {"path": widget_service.open_personal_workouts_folder()}
