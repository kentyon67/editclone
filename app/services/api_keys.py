"""
外部APIキー管理サービス（Phase 6-4: 外部API公開）
ユーザーが外部ツール・スクリプトから EditClone API を叩くためのキー管理。
"""
import datetime
import hashlib
import logging
import secrets
from typing import Optional

logger = logging.getLogger(__name__)

_KEY_PREFIX = "eck_"


def _client():
    from app.services.storage import _client as sc
    return sc()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_api_key(user_id: str, name: str) -> dict:
    """新しいAPIキーを生成。raw_key は一度だけ返す（以降復元不能）。"""
    raw = _KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = _hash_key(raw)
    prefix = raw[:16]  # 表示用プレフィックス

    try:
        resp = _client().table("api_keys").insert({
            "user_id": user_id,
            "name": name,
            "key_hash": key_hash,
            "key_prefix": prefix,
            "revoked": False,
        }).execute()
        row = resp.data[0] if resp.data else {}
        return {**row, "raw_key": raw}
    except Exception as e:
        logger.warning("create_api_key failed: %s", e)
        raise RuntimeError("APIキーの作成に失敗しました") from e


def list_api_keys(user_id: str) -> list[dict]:
    try:
        resp = (
            _client().table("api_keys")
            .select("id, name, key_prefix, revoked, last_used_at, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_api_keys failed: %s", e)
        return []


def revoke_api_key(user_id: str, key_id: str) -> bool:
    try:
        _client().table("api_keys").update({"revoked": True}).eq(
            "id", key_id
        ).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("revoke_api_key failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# 認証
# ---------------------------------------------------------------------------

def validate_api_key(raw_key: str) -> Optional[dict]:
    """APIキーを検証しユーザー情報を返す。無効なら None。"""
    if not raw_key.startswith(_KEY_PREFIX):
        return None

    key_hash = _hash_key(raw_key)
    try:
        resp = (
            _client().table("api_keys")
            .select("id, user_id")
            .eq("key_hash", key_hash)
            .eq("revoked", False)
            .limit(1)
            .execute()
        )
        if not resp.data:
            return None

        row = resp.data[0]
        # last_used_at を非同期的に更新（失敗してもOK）
        try:
            _client().table("api_keys").update({
                "last_used_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }).eq("id", row["id"]).execute()
        except Exception:
            pass

        return {"id": row["user_id"], "email": ""}
    except Exception as e:
        logger.warning("validate_api_key failed: %s", e)
        return None
