from fastapi import APIRouter, Depends

from app.middleware.auth import require_user
from app.services.usage import PLAN_LIMITS, PLAN_MAX_DURATIONS, get_current_usage, get_user_plan

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/me")
async def get_my_usage(user: dict = Depends(require_user)):
    plan = get_user_plan(user["id"])
    used = get_current_usage(user["id"])
    limit = PLAN_LIMITS.get(plan)
    max_duration = PLAN_MAX_DURATIONS.get(plan)

    return {
        "plan": plan,
        "used": used,
        "limit": limit,
        "remaining": None if limit is None else max(0, limit - used),
        "max_duration_seconds": max_duration,
    }
