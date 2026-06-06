"""Webhook管理ルーター（Phase 6-4: Webhook連携）"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.middleware.auth import require_user
import app.services.webhooks as svc

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class CreateWebhookBody(BaseModel):
    url: str = Field(..., min_length=8, description="HTTPS/HTTPエンドポイントURL")
    events: List[str] = Field(
        default=["job.completed", "job.failed"],
        description="受信するイベント一覧",
    )


@router.get("")
def list_webhooks(user: dict = Depends(require_user)):
    return {"webhooks": svc.list_webhooks(user["id"])}


@router.post("")
def create_webhook(body: CreateWebhookBody, user: dict = Depends(require_user)):
    try:
        result = svc.register_webhook(user["id"], body.url, body.events)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: str, user: dict = Depends(require_user)):
    svc.delete_webhook(user["id"], webhook_id)
    return {"deleted": True}
