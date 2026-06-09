"""
管理者専用エンドポイント。
認証: X-Admin-Token ヘッダー = SUPABASE_SERVICE_ROLE_KEY

エンドポイント一覧:
  GET  /admin/migrations          — マイグレーション状態確認
  POST /admin/migrations/run      — 未適用マイグレーションを実行
  POST /admin/migrations/run-sql  — 任意SQLを直接実行
  GET  /admin/health              — サービス全体のヘルスチェック
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/admin", tags=["admin"])

_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _require_admin(x_admin_token: Optional[str] = Header(default=None)):
    """SUPABASE_SERVICE_ROLE_KEY を X-Admin-Token ヘッダーで検証する。"""
    if not _ROLE_KEY:
        raise HTTPException(503, "Admin not configured (SUPABASE_SERVICE_ROLE_KEY 未設定)")
    if x_admin_token != _ROLE_KEY:
        raise HTTPException(403, "Invalid admin token")
    return True


class RunSqlBody(BaseModel):
    sql: str
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/migrations")
def get_migration_status(_=Depends(_require_admin)):
    """全マイグレーションの適用状況を返す。"""
    from app.services.migrations import check_status
    return {"migrations": check_status()}


@router.post("/migrations/run")
def run_migrations(dry_run: bool = False, _=Depends(_require_admin)):
    """
    未適用マイグレーションを実行する。
    dry_run=true の場合は実行せず対象のみ返す。
    """
    from app.services.migrations import run_pending
    result = run_pending(dry_run=dry_run)
    ok = len(result["errors"]) == 0
    return {
        "success": ok,
        "dry_run": dry_run,
        **result,
    }


@router.post("/migrations/run-sql")
def run_sql(body: RunSqlBody, _=Depends(_require_admin)):
    """任意のSQLを直接実行する。本番DBへの直接操作。慎重に使用すること。"""
    from app.services.migrations import run_sql_direct
    try:
        rows = run_sql_direct(body.sql)
        return {"success": True, "rows": rows}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/health")
def admin_health(_=Depends(_require_admin)):
    """詳細なシステムヘルス情報を返す。"""
    import os
    from app.services.migrations import check_status, _project_ref

    env_check = {
        "SUPABASE_URL":          bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(os.environ.get("SUPABASE_SERVICE_ROLE_KEY")),
        "SUPABASE_ACCESS_TOKEN": bool(os.environ.get("SUPABASE_ACCESS_TOKEN")),
        "ANTHROPIC_API_KEY":     bool(os.environ.get("ANTHROPIC_API_KEY")),
        "STRIPE_SECRET_KEY":     bool(os.environ.get("STRIPE_SECRET_KEY")),
    }

    migration_status = check_status()
    pending = [m for m in migration_status if m["status"] == "pending"]

    return {
        "project_ref":      _project_ref() or "unknown",
        "env":              env_check,
        "migrations":       migration_status,
        "pending_count":    len(pending),
        "all_applied":      len(pending) == 0,
    }
