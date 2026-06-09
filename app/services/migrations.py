"""
Supabase マイグレーション自動実行サービス。

仕組み:
  1. supabase/schema.sql  → ベーススキーマ（全テーブル・RLS・関数）
  2. supabase/migration_v*.sql → 追加マイグレーション（番号順）
  3. schema_migrations テーブルで適用済みを追跡（初回は Management API で作成）
  4. 未適用のマイグレーションのみ実行

必要な環境変数:
  SUPABASE_URL           - https://{project-ref}.supabase.co
  SUPABASE_ACCESS_TOKEN  - supabase.com/dashboard/account/tokens で取得
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "supabase"

# Management API で実行済みを追跡するテーブル（最初に作成）
_CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS public.schema_migrations (
  id        serial primary key,
  name      text not null unique,
  applied_at timestamptz default now()
);
"""

# migration ファイルの順序定義
_MIGRATION_FILES: list[tuple[str, str]] = [
    ("schema_v5",      "schema.sql"),
    ("migration_v8",   "migration_v8.sql"),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _project_ref() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    m = re.match(r"https://([^.]+)\.supabase\.co", url)
    return m.group(1) if m else ""


def _management_api_query(sql: str) -> list[dict]:
    """Supabase Management API でSQLを実行する。"""
    ref   = _project_ref()
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    if not ref or not token:
        raise RuntimeError(
            "SUPABASE_ACCESS_TOKEN または SUPABASE_URL が未設定。"
            " supabase.com/dashboard/account/tokens でトークンを取得してください。"
        )
    url     = f"https://api.supabase.com/v1/projects/{ref}/database/query"
    payload = json.dumps({"query": sql}).encode()
    req     = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type",  "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()) or []
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Management API エラー {e.code}: {body}") from e


def _get_applied_migrations() -> set[str]:
    """適用済みマイグレーション名セットを返す。テーブルがなければ空セット。"""
    try:
        rows = _management_api_query(
            "SELECT name FROM public.schema_migrations ORDER BY id;"
        )
        return {r["name"] for r in (rows or [])}
    except Exception:
        return set()


def _mark_applied(name: str) -> None:
    _management_api_query(
        f"INSERT INTO public.schema_migrations (name) "
        f"VALUES ('{name}') ON CONFLICT (name) DO NOTHING;"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_status() -> list[dict]:
    """
    全マイグレーションのステータス一覧を返す。
    [{"name": "schema_v5", "status": "applied" | "pending", "file": "schema.sql"}, ...]
    """
    ref   = _project_ref()
    token = os.environ.get("SUPABASE_ACCESS_TOKEN", "")
    if not ref or not token:
        return [
            {"name": n, "file": f, "status": "unknown", "reason": "SUPABASE_ACCESS_TOKEN 未設定"}
            for n, f in _MIGRATION_FILES
        ]
    applied = _get_applied_migrations()
    return [
        {
            "name":   name,
            "file":   fname,
            "status": "applied" if name in applied else "pending",
        }
        for name, fname in _MIGRATION_FILES
    ]


def run_pending(dry_run: bool = False) -> dict:
    """
    未適用のマイグレーションをすべて実行する。

    Returns:
        {"applied": [...], "skipped": [...], "errors": [...]}
    """
    # まず tracking テーブルを確保
    try:
        _management_api_query(_CREATE_TRACKING_TABLE)
    except Exception as e:
        return {"applied": [], "skipped": [], "errors": [f"tracking table 作成失敗: {e}"]}

    applied_names = _get_applied_migrations()
    results: dict[str, list] = {"applied": [], "skipped": [], "errors": []}

    for name, fname in _MIGRATION_FILES:
        if name in applied_names:
            results["skipped"].append(name)
            continue

        sql_path = _MIGRATIONS_DIR / fname
        if not sql_path.exists():
            results["errors"].append(f"{fname} が見つかりません: {sql_path}")
            continue

        sql = sql_path.read_text(encoding="utf-8")
        if dry_run:
            results["applied"].append({"name": name, "dry_run": True, "sql_bytes": len(sql)})
            continue

        try:
            _management_api_query(sql)
            _mark_applied(name)
            results["applied"].append({"name": name, "sql_bytes": len(sql)})
            logger.info("マイグレーション適用: %s (%d bytes)", name, len(sql))
        except Exception as e:
            err_msg = f"{name} 実行失敗: {e}"
            results["errors"].append(err_msg)
            logger.error(err_msg)
            break  # 失敗したら後続をスキップ（依存関係保護）

    return results


def run_sql_direct(sql: str) -> list[dict]:
    """任意のSQLを直接実行する（管理者専用）。"""
    return _management_api_query(sql)
