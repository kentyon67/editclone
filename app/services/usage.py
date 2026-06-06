import os
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

PLAN_LIMITS: dict[str, int | None] = {
    "free": 5,
    "pro": 30,
    "creator": 100,
    "studio": None,
}

PLAN_MAX_DURATIONS: dict[str, float | None] = {
    "free": 300.0,
    "pro": 900.0,
    "creator": 3600.0,
    "studio": None,
}


class LimitExceededError(Exception):
    def __init__(self, current: int, limit: int, plan: str):
        self.current = current
        self.limit = limit
        self.plan = plan
        super().__init__(f"Monthly limit exceeded: {current}/{limit} ({plan})")


class DurationExceededError(Exception):
    def __init__(self, duration: float, max_duration: float, plan: str):
        self.duration = duration
        self.max_duration = max_duration
        self.plan = plan
        super().__init__(f"Video too long: {duration:.0f}s > {max_duration:.0f}s ({plan})")


def _client():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _year_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_user_plan(user_id: str) -> str:
    if not USE_SUPABASE:
        return "studio"
    try:
        res = _client().table("profiles").select("plan").eq("id", user_id).single().execute()
        return res.data.get("plan", "free") if res.data else "free"
    except Exception:
        return "free"


def get_current_usage(user_id: str) -> int:
    if not USE_SUPABASE:
        return 0
    try:
        res = (
            _client()
            .table("usage_logs")
            .select("video_count")
            .eq("user_id", user_id)
            .eq("year_month", _year_month())
            .execute()
        )
        return res.data[0]["video_count"] if res.data else 0
    except Exception:
        return 0


def increment_usage(user_id: str) -> None:
    """使用回数をインクリメント。失敗時は例外を raise する（呼び出し側でハンドリング）。"""
    if not USE_SUPABASE:
        return
    ym = _year_month()
    try:
        _client().rpc("increment_usage", {"p_user_id": user_id, "p_year_month": ym}).execute()
        return
    except Exception:
        pass
    # RPC が未登録の場合は直接 upsert にフォールバック
    current = get_current_usage(user_id)
    _client().table("usage_logs").upsert({
        "user_id": user_id,
        "year_month": ym,
        "video_count": current + 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()


def check_and_increment(user_id: str, plan: str) -> int:
    """上限チェック後インクリメント。超過時は LimitExceededError。戻り値: インクリメント後の使用本数。"""
    limit = PLAN_LIMITS.get(plan)
    current = get_current_usage(user_id)

    if limit is not None and current >= limit:
        raise LimitExceededError(current=current, limit=limit, plan=plan)

    increment_usage(user_id)
    return current + 1


def check_duration(duration_seconds: float | None, plan: str) -> None:
    """動画長がプラン上限を超えていれば DurationExceededError。"""
    if duration_seconds is None:
        return
    max_dur = PLAN_MAX_DURATIONS.get(plan)
    if max_dur is not None and duration_seconds > max_dur:
        raise DurationExceededError(duration=duration_seconds, max_duration=max_dur, plan=plan)
