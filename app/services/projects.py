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


# ---------------------------------------------------------------------------
# Re-export (Phase 3)
# ---------------------------------------------------------------------------

def re_export_project(project_id: str, user_id: str, prompt: Optional[str] = None) -> str:
    """元ジョブ設定で再処理を実行する。新しいジョブIDを返す。"""
    project = get_project(project_id, user_id)
    if project is None:
        raise PermissionError("プロジェクトが見つかりません")

    from app.services.jobs import get_job, create_job
    source_job = get_job(project["source_job_id"])
    if source_job is None:
        raise ValueError("元ジョブが見つかりません（元動画が期限切れの可能性があります）")

    new_prompt = prompt if prompt is not None else (source_job.prompt or "")
    new_job = create_job(
        video_id=source_job.video_id,
        video_path=source_job.video_path,
        noise_db=source_job.noise_db,
        min_duration=source_job.min_duration,
        user_id=user_id,
        prompt=new_prompt,
    )
    return new_job.id


# ---------------------------------------------------------------------------
# Plugin Revision Receive + Conflict Detection (Phase 3)
# ---------------------------------------------------------------------------

def receive_plugin_revision(
    project_id: str,
    user_id: str,
    notes: str = "",
    metadata: Optional[dict] = None,
) -> dict:
    """Plugin からのリビジョンを受信し、競合を検出する。学習シグナルも抽出する。"""
    project = get_project(project_id, user_id)
    if project is None:
        raise PermissionError("プロジェクトが見つかりません")

    existing = project.get("project_revisions") or []
    next_num = get_next_revision_number(project_id)

    # 直近の plugin リビジョンより後に web リビジョンがあれば競合
    last_plugin = next(
        (r for r in sorted(existing, key=lambda x: x.get("revision_number", 0), reverse=True)
         if r.get("source") == "plugin"),
        None,
    )
    if last_plugin:
        web_after = [
            r for r in existing
            if r.get("source") == "web"
            and r.get("revision_number", 0) > last_plugin.get("revision_number", 0)
        ]
        is_conflict = len(web_after) > 0
    else:
        is_conflict = False

    revision = add_revision(
        project_id=project_id,
        user_id=user_id,
        revision_number=next_num,
        source="plugin",
        notes=notes,
        metadata=metadata or {},
    )

    new_status = "conflict" if is_conflict else "synced"
    update_sync_status(project_id, user_id, new_status)

    # Plugin の編集内容からスタイル学習シグナルを非同期抽出
    try:
        _learn_from_plugin_revision(project, user_id, metadata or {})
    except Exception as e:
        logger.debug("revision learning failed: %s", e)

    return {"revision": revision, "sync_status": new_status}


def _learn_from_plugin_revision(project: dict, user_id: str, metadata: dict) -> None:
    """
    Plugin が送信した metadata から学習シグナルを抽出し feedback_logs に記録する。

    Plugin 側が送信できる metadata フィールド（全てオプション）:
      - cuts_accepted: int        — 採用したカット数
      - cuts_rejected: int        — 却下したカット数（追加で戻したカット）
      - manual_adjustments: int   — 手動でタイミングを調整した箇所数
      - action: "accept" | "reject" | "partial"  — 全体評価（省略時は自動判定）
      - notes: str                — 自由コメント
    """
    cuts_accepted = int(metadata.get("cuts_accepted", 0))
    cuts_rejected = int(metadata.get("cuts_rejected", 0))
    manual_adj = int(metadata.get("manual_adjustments", 0))
    explicit_action = metadata.get("action", "")
    notes = str(metadata.get("notes", "")).strip()

    total = cuts_accepted + cuts_rejected
    if total == 0 and not explicit_action:
        return  # 有効なシグナルなし

    # action を自動判定（explicit が優先）
    if explicit_action in ("accept", "reject", "partial"):
        action = explicit_action
    elif total > 0:
        accept_rate = cuts_accepted / total
        if accept_rate >= 0.9 and manual_adj == 0:
            action = "accept"
        elif accept_rate >= 0.5:
            action = "partial"
        else:
            action = "reject"
    else:
        return

    auto_notes = notes
    if not auto_notes:
        parts = []
        if cuts_rejected > 0:
            parts.append(f"カット {cuts_rejected}箇所を復元")
        if manual_adj > 0:
            parts.append(f"タイミング {manual_adj}箇所を調整")
        if cuts_accepted > 0:
            parts.append(f"カット {cuts_accepted}箇所を採用")
        auto_notes = "、".join(parts) if parts else "Plugin 編集から自動記録"

    # プロジェクトに関連する Style Profile ID を取得
    style_profile_id = project.get("style_profile_id")
    source_job_id = project.get("source_job_id", "plugin-revision")

    from app.services.style_profiles import record_feedback
    record_feedback(
        user_id=user_id,
        job_id=source_job_id,
        action=action,
        style_profile_id=style_profile_id,
        notes=auto_notes,
    )
    logger.info("plugin revision learning: action=%s, profile=%s", action, style_profile_id)
