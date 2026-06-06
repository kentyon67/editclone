"""
チーム管理 API (Phase 6-4: Studio プラン限定)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.middleware.auth import require_user
from app.services import teams as svc
from app.services.usage import get_user_plan

router = APIRouter(prefix="/teams", tags=["teams"])


def _require_studio(user: dict):
    plan = get_user_plan(user["id"])
    if plan != "studio":
        raise HTTPException(
            status_code=403,
            detail={"code": "PLAN_REQUIRED", "plan": "studio", "message": "チーム機能は Studio プランのみ利用できます"},
        )


# ---------------------------------------------------------------------------
# Team info
# ---------------------------------------------------------------------------

@router.get("")
def get_team(user: dict = Depends(require_user)):
    """オーナーとしてのチームメンバー一覧と、招待されているチーム一覧を返す。"""
    _require_studio(user)
    return {
        "my_team": svc.get_team(user["id"]),
        "joined_teams": svc.get_my_teams(user["id"]),
    }


# ---------------------------------------------------------------------------
# Invite
# ---------------------------------------------------------------------------

class InviteBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    role: str = Field("editor", pattern="^(editor|admin)$")


@router.post("/invite")
def invite_member(body: InviteBody, user: dict = Depends(require_user)):
    """メールアドレスでチームに招待する（Studio プランのみ）。"""
    _require_studio(user)
    try:
        invite = svc.invite_member(user["id"], body.email, body.role)
        if invite is None:
            raise HTTPException(status_code=500, detail="招待の作成に失敗しました")
        return invite
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Invitation acceptance (no plan check — invitee may be on any plan)
# ---------------------------------------------------------------------------

@router.get("/invitations/{token}")
def get_invite_info(token: str):
    """招待トークンの情報を返す（認証不要・招待確認画面で使用）。"""
    invite = svc.get_invite_by_token(token)
    if invite is None:
        raise HTTPException(status_code=404, detail="招待が見つかりません")
    # セキュリティのため owner_id は返さない
    return {
        "invited_email": invite["invited_email"],
        "role": invite["role"],
        "status": invite["status"],
    }


@router.post("/invitations/{token}/accept")
def accept_invite(token: str, user: dict = Depends(require_user)):
    """招待を承認してチームに参加する。"""
    try:
        result = svc.accept_invite(token, user["id"], user.get("email", ""))
        if result is None:
            raise HTTPException(status_code=500, detail="承認処理に失敗しました")
        return {"accepted": True, "role": result.get("role")}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Remove member
# ---------------------------------------------------------------------------

@router.delete("/members/{member_row_id}")
def remove_member(member_row_id: str, user: dict = Depends(require_user)):
    """チームメンバーを削除する（オーナーのみ）。"""
    _require_studio(user)
    ok = svc.remove_member(user["id"], member_row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="メンバーが見つかりません")
    return {"removed": True}


# ---------------------------------------------------------------------------
# Shared style profiles
# ---------------------------------------------------------------------------

@router.get("/{owner_id}/style-profiles")
def team_style_profiles(owner_id: str, user: dict = Depends(require_user)):
    """チームオーナーのスタイルプロファイルにアクセスする（チームメンバーのみ）。"""
    try:
        profiles = svc.get_team_profiles(owner_id, user["id"])
        return {"profiles": profiles}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
