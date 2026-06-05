from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware.auth import require_user
from app.services import projects as svc

router = APIRouter(prefix="/projects", tags=["projects"])


class SyncStatusUpdate(BaseModel):
    sync_status: str


@router.get("")
def list_projects(user: dict = Depends(require_user)):
    return {"projects": svc.list_projects(user["id"])}


@router.get("/{project_id}")
def get_project(project_id: str, user: dict = Depends(require_user)):
    project = svc.get_project(project_id, user["id"])
    if project is None:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
    return project


@router.patch("/{project_id}/sync-status")
def update_sync_status(
    project_id: str,
    body: SyncStatusUpdate,
    user: dict = Depends(require_user),
):
    if body.sync_status not in ("local", "synced", "conflict"):
        raise HTTPException(status_code=400, detail="無効な sync_status です")
    ok = svc.update_sync_status(project_id, user["id"], body.sync_status)
    if not ok:
        raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
    return {"updated": True}
