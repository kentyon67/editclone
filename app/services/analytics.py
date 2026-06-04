import os
from datetime import datetime, timezone
from typing import Any

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def _client():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def log_event(
    event_type: str,
    user_id: str | None = None,
    video_id: str | None = None,
    job_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """非同期ログ。失敗しても呼び出し元に影響しない。"""
    if not USE_SUPABASE:
        return
    try:
        row: dict[str, Any] = {
            "event_type": event_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if user_id:
            row["user_id"] = user_id
        if video_id:
            row["video_id"] = video_id
        if job_id:
            row["job_id"] = job_id
        if metadata:
            row["metadata"] = metadata
        _client().table("analytics_events").insert(row).execute()
    except Exception:
        pass
