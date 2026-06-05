"""Phase 3: プロジェクト管理 — エクスポート履歴 + Plugin Sync 基盤"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _client():
    from app.services.storage import _client as storage_client
    return storage_client()


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

def create_project(
    user_id: str,
    name: str,
    source_job_id: str,
    style_profile_id: Optional[str] = None,
) -> Optional[dict]:
    try:
        resp = _client().table("projects").insert({
            "user_id": user_id,
            "name": name,
            "source_job_id": source_job_id,
            "style_profile_id": style_profile_id,
            "sync_status": "local",
        }).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("create_project failed: %s", e)
        return None


def list_projects(user_id: str, limit: int = 20) -> list[dict]:
    try:
        resp = (
            _client().table("projects")
            .select("*, project_revisions(id, revision_number, source, created_at)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_projects failed: %s", e)
        return []


def get_project(project_id: str, user_id: str) -> Optional[dict]:
    try:
        resp = (
            _client().table("projects")
            .select("*, project_revisions(*)")
            .eq("id", project_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_project failed: %s", e)
        return None


def update_sync_status(project_id: str, user_id: str, status: str) -> bool:
    try:
        import datetime
        _client().table("projects").update({
            "sync_status": status,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("id", project_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("update_sync_status failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Revision CRUD
# ---------------------------------------------------------------------------

def add_revision(
    project_id: str,
    user_id: str,
    revision_number: int,
    source: str = "web",
    notes: str = "",
    result_path: str = "",
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    try:
        resp = _client().table("project_revisions").insert({
            "project_id": project_id,
            "user_id": user_id,
            "revision_number": revision_number,
            "source": source,
            "notes": notes,
            "result_path": result_path,
            "metadata": metadata or {},
        }).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("add_revision failed: %s", e)
        return None


def get_next_revision_number(project_id: str) -> int:
    try:
        resp = (
            _client().table("project_revisions")
            .select("revision_number")
            .eq("project_id", project_id)
            .order("revision_number", desc=True)
            .limit(1)
            .execute()
        )
        return (resp.data[0]["revision_number"] + 1) if resp.data else 1
    except Exception as e:
        logger.warning("get_next_revision_number failed: %s", e)
        return 1
