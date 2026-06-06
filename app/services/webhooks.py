"""
Webhook配信サービス（Phase 6-4: Webhook連携）
ジョブ完了・失敗時に登録済みURLへHTTP POSTを送信する。
ペイロードにはHMACシグネチャを付与してなりすまし防止。
"""
import datetime
import hashlib
import hmac
import json
import logging
import secrets
import threading
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

ALLOWED_EVENTS = {"job.completed", "job.failed"}


def _client():
    from app.services.storage import _client as sc
    return sc()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def register_webhook(user_id: str, url: str, events: list[str]) -> dict:
    """Webhookを登録。secretは登録時のみ返す。"""
    filtered = [e for e in events if e in ALLOWED_EVENTS]
    if not filtered:
        raise ValueError(f"有効なイベントを指定してください: {sorted(ALLOWED_EVENTS)}")

    secret = secrets.token_hex(32)
    try:
        resp = _client().table("webhooks").insert({
            "user_id": user_id,
            "url": url,
            "events": filtered,
            "secret": secret,
            "active": True,
        }).execute()
        row = resp.data[0] if resp.data else {}
        return {**row, "secret": secret}
    except Exception as e:
        logger.warning("register_webhook failed: %s", e)
        raise RuntimeError("Webhookの登録に失敗しました") from e


def list_webhooks(user_id: str) -> list[dict]:
    try:
        resp = (
            _client().table("webhooks")
            .select("id, url, events, active, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_webhooks failed: %s", e)
        return []


def delete_webhook(user_id: str, webhook_id: str) -> bool:
    try:
        _client().table("webhooks").delete().eq(
            "id", webhook_id
        ).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("delete_webhook failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# 配信
# ---------------------------------------------------------------------------

def trigger_webhooks(user_id: str, event: str, payload: dict) -> None:
    """指定イベントに対応する全Webhookを非同期で呼び出す。"""
    try:
        resp = (
            _client().table("webhooks")
            .select("id, url, secret")
            .eq("user_id", user_id)
            .eq("active", True)
            .contains("events", [event])
            .execute()
        )
        hooks = resp.data or []
    except Exception as e:
        logger.warning("trigger_webhooks fetch failed: %s", e)
        return

    for hook in hooks:
        threading.Thread(
            target=_deliver,
            args=(hook["url"], hook["secret"], event, payload),
            daemon=True,
        ).start()


def _deliver(url: str, secret: str, event: str, payload: dict) -> None:
    body = json.dumps({
        "event": event,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        **payload,
    }).encode()

    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-EditClone-Signature": f"sha256={sig}",
            "X-EditClone-Event": event,
            "User-Agent": "EditClone-Webhook/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                logger.warning("Webhook %s delivery failed: HTTP %s", url, resp.status)
    except Exception as e:
        logger.warning("Webhook %s delivery error: %s", url, e)
