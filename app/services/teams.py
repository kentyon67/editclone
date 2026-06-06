"""
チーム管理サービス（Phase 6-4: Studio プラン限定）
チームオーナーがメンバーを招待し、スタイルプロファイルを共有できる。
"""
import logging
import secrets
import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _client():
    from app.services.storage import _client as storage_client
    return storage_client()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Team CRUD
# ---------------------------------------------------------------------------

def get_team(owner_id: str) -> dict:
    """オーナーのチーム情報（メンバー一覧含む）を返す。"""
    try:
        resp = (
            _client().table("team_members")
            .select("id, invited_email, member_id, role, status, created_at")
            .eq("owner_id", owner_id)
            .order("created_at", desc=False)
            .execute()
        )
        return {"members": resp.data or []}
    except Exception as e:
        logger.warning("get_team failed: %s", e)
        return {"members": []}


def get_my_teams(user_id: str) -> list[dict]:
    """自分が招待されているチーム（承認済み）を返す。"""
    try:
        resp = (
            _client().table("team_members")
            .select("id, owner_id, role, status, created_at")
            .eq("member_id", user_id)
            .eq("status", "accepted")
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("get_my_teams failed: %s", e)
        return []


def invite_member(owner_id: str, invited_email: str, role: str = "editor") -> Optional[dict]:
    """
    メンバーをチームに招待する。
    招待トークンを生成し、DBに保存する。メール送信は呼び出し元が担う。
    """
    if role not in ("editor", "admin"):
        raise ValueError("role は 'editor' または 'admin' のみ指定できます")

    # 既存招待確認（同じオーナー+メールの招待が既にある場合は再利用）
    try:
        existing = (
            _client().table("team_members")
            .select("*")
            .eq("owner_id", owner_id)
            .eq("invited_email", invited_email)
            .limit(1)
            .execute()
        )
        if existing.data:
            row = existing.data[0]
            if row["status"] == "accepted":
                raise ValueError("このメンバーはすでにチームに参加しています")
            # pending の場合はトークンを再生成して返す
            token = secrets.token_urlsafe(32)
            _client().table("team_members").update({
                "invite_token": token,
                "role": role,
                "updated_at": _now(),
            }).eq("id", row["id"]).execute()
            row["invite_token"] = token
            return row
    except ValueError:
        raise
    except Exception:
        pass

    token = secrets.token_urlsafe(32)
    try:
        resp = _client().table("team_members").insert({
            "owner_id": owner_id,
            "invited_email": invited_email,
            "role": role,
            "status": "pending",
            "invite_token": token,
        }).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("invite_member failed: %s", e)
        return None


def get_invite_by_token(token: str) -> Optional[dict]:
    """招待トークンから招待情報を取得する（認証不要）。"""
    try:
        resp = (
            _client().table("team_members")
            .select("id, owner_id, invited_email, role, status")
            .eq("invite_token", token)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_invite_by_token failed: %s", e)
        return None


def accept_invite(token: str, user_id: str, user_email: str) -> Optional[dict]:
    """
    招待を承認する。
    招待メールアドレスとログインユーザーのメールアドレスが一致している必要がある。
    """
    invite = get_invite_by_token(token)
    if invite is None:
        raise ValueError("招待が見つかりません")
    if invite["status"] != "pending":
        raise ValueError("この招待はすでに処理済みです")
    if invite["invited_email"].lower() != user_email.lower():
        raise PermissionError("招待されたメールアドレスと異なります")

    try:
        resp = _client().table("team_members").update({
            "member_id": user_id,
            "status": "accepted",
            "updated_at": _now(),
        }).eq("invite_token", token).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("accept_invite failed: %s", e)
        return None


def remove_member(owner_id: str, member_id_or_row_id: str) -> bool:
    """チームメンバーを削除する（オーナーのみ）。"""
    try:
        _client().table("team_members").delete().eq(
            "id", member_id_or_row_id
        ).eq("owner_id", owner_id).execute()
        return True
    except Exception as e:
        logger.warning("remove_member failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Shared Style Profiles
# ---------------------------------------------------------------------------

def get_team_profiles(owner_id: str, requester_id: str) -> list[dict]:
    """
    チームメンバーがオーナーのスタイルプロファイルにアクセスする。
    requester_id がオーナーのチームに accepted メンバーとして存在する場合のみ返す。
    """
    try:
        # メンバーシップ確認
        check = (
            _client().table("team_members")
            .select("id")
            .eq("owner_id", owner_id)
            .eq("member_id", requester_id)
            .eq("status", "accepted")
            .limit(1)
            .execute()
        )
        if not check.data:
            raise PermissionError("このチームのメンバーではありません")

        from app.services.style_profiles import list_profiles
        return list_profiles(owner_id)
    except PermissionError:
        raise
    except Exception as e:
        logger.warning("get_team_profiles failed: %s", e)
        return []
