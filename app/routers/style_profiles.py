from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.middleware.auth import require_user
from app.services import style_profiles as svc

router = APIRouter(prefix="/style-profiles", tags=["style-profiles"])


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = ""
    noise_db: float = -30.0
    min_silence_seconds: float = 0.5
    default_prompt: str = ""


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    description: Optional[str] = None
    noise_db: Optional[float] = None
    min_silence_seconds: Optional[float] = None
    default_prompt: Optional[str] = None


class FeedbackCreate(BaseModel):
    job_id: str
    action: str = Field(..., pattern="^(accept|reject|partial)$")
    style_profile_id: Optional[str] = None
    notes: str = ""


class RefVideoCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=500)


@router.get("")
def list_profiles(user: dict = Depends(require_user)):
    return {"profiles": svc.list_profiles(user["id"])}


@router.post("")
def create_profile(body: ProfileCreate, user: dict = Depends(require_user)):
    profile = svc.create_profile(user["id"], body.model_dump())
    if profile is None:
        raise HTTPException(status_code=500, detail="プロファイルの作成に失敗しました")
    return profile


@router.get("/active")
def get_active(user: dict = Depends(require_user)):
    profile = svc.get_active_profile(user["id"])
    return {"profile": profile}


@router.get("/{profile_id}")
def get_profile(profile_id: str, user: dict = Depends(require_user)):
    profile = svc.get_profile(profile_id, user["id"])
    if profile is None:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


@router.put("/{profile_id}")
def update_profile(profile_id: str, body: ProfileUpdate, user: dict = Depends(require_user)):
    profile = svc.update_profile(profile_id, user["id"], body.model_dump(exclude_none=True))
    if profile is None:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


@router.delete("/{profile_id}")
def delete_profile(profile_id: str, user: dict = Depends(require_user)):
    ok = svc.delete_profile(profile_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return {"deleted": True}


@router.post("/{profile_id}/activate")
def activate_profile(profile_id: str, user: dict = Depends(require_user)):
    ok = svc.set_active_profile(profile_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return {"activated": True}


@router.post("/feedback")
def post_feedback(body: FeedbackCreate, user: dict = Depends(require_user)):
    ok = svc.record_feedback(
        user_id=user["id"],
        job_id=body.job_id,
        action=body.action,
        style_profile_id=body.style_profile_id,
        notes=body.notes,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="フィードバックの記録に失敗しました")
    return {"recorded": True}


# ---------------------------------------------------------------------------
# Reference Videos
# ---------------------------------------------------------------------------

@router.get("/{profile_id}/reference-videos")
def list_ref_videos(profile_id: str, user: dict = Depends(require_user)):
    return {"videos": svc.list_reference_videos(profile_id, user["id"])}


@router.post("/{profile_id}/reference-videos")
def add_ref_video(profile_id: str, body: RefVideoCreate, user: dict = Depends(require_user)):
    try:
        video = svc.add_reference_video(profile_id, user["id"], body.url)
        return video
    except PermissionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"参考動画の追加に失敗しました: {e}")


@router.delete("/{profile_id}/reference-videos/{video_id}")
def delete_ref_video(profile_id: str, video_id: str, user: dict = Depends(require_user)):
    ok = svc.delete_reference_video(video_id, profile_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="参考動画が見つかりません")
    return {"deleted": True}
