import os
from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
AUTH_ENABLED = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


@lru_cache(maxsize=1)
def _get_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """
    Supabase JWT を検証してユーザー情報を返す。
    環境変数が未設定の場合（ローカル開発）は認証をスキップして None を返す。
    """
    if not AUTH_ENABLED:
        return None

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = authorization.removeprefix("Bearer ")
    try:
        supabase = _get_supabase()
        response = supabase.auth.get_user(token)
        return {"id": response.user.id, "email": response.user.email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """認証必須。未認証なら401を返す。ローカル開発ではダミーユーザーを返す。"""
    if not AUTH_ENABLED:
        return {"id": "dev-user", "email": "dev@localhost"}
    user = await get_current_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
