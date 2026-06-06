"""外部APIキー管理ルーター（Phase 6-4: 外部API公開）"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import require_user
import app.services.api_keys as svc

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateKeyBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


@router.get("")
def list_keys(user: dict = Depends(require_user)):
    return {"api_keys": svc.list_api_keys(user["id"])}


@router.post("")
def create_key(body: CreateKeyBody, user: dict = Depends(require_user)):
    try:
        return svc.create_api_key(user["id"], body.name)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key_id}")
def revoke_key(key_id: str, user: dict = Depends(require_user)):
    svc.revoke_api_key(user["id"], key_id)
    return {"revoked": True}
