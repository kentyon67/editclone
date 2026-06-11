import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from typing import List, Optional

from app.middleware.auth import require_user
from app.services import style_profiles as svc

router = APIRouter(prefix="/style-profiles", tags=["style-profiles"])


class CaptionStyle(BaseModel):
    font_size: int = Field(28, ge=12, le=72)
    position: str = Field("bottom", pattern="^(bottom|top|middle)$")
    primary_color: str = Field("#FFFFFF", pattern="^#[0-9A-Fa-f]{6}$")
    outline_color: str = Field("#000000", pattern="^#[0-9A-Fa-f]{6}$")
    bold: bool = True
    zoom_effect: Optional[str] = Field("none", pattern="^(none|subtle|punch)$")


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str = ""
    noise_db: float = -30.0
    min_silence_seconds: float = 0.5
    default_prompt: str = ""
    caption_style: Optional[CaptionStyle] = None


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    description: Optional[str] = None
    noise_db: Optional[float] = None
    min_silence_seconds: Optional[float] = None
    default_prompt: Optional[str] = None
    caption_style: Optional[CaptionStyle] = None


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


@router.get("/{profile_id}/stats")
def profile_stats(profile_id: str, user: dict = Depends(require_user)):
    """フィードバック統計（accept/partial/reject 件数）を返す。"""
    return svc.get_profile_stats(profile_id, user["id"])


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


# ---------------------------------------------------------------------------
# AI Profile Refinement
# ---------------------------------------------------------------------------

@router.post("/{profile_id}/ai-refine")
def ai_refine(profile_id: str, user: dict = Depends(require_user)):
    try:
        suggested = svc.ai_refine_profile(profile_id, user["id"])
        return {"suggested_prompt": suggested}
    except PermissionError:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI改善の生成に失敗しました: {e}")


# ---------------------------------------------------------------------------
# Edit DNA — 編集前後ペア分析
# ---------------------------------------------------------------------------

_PAIR_ALLOWED_EXT = {".mp4", ".mov", ".m4v"}


@router.post("/analyze-pair")
async def analyze_edit_pair(
    before: UploadFile = File(..., description="未編集の元動画"),
    after: UploadFile = File(..., description="ユーザーが編集した完成動画"),
    user: dict = Depends(require_user),
):
    """
    編集前後の動画ペアを分析し、編集スタイル DNA（カット傾向・推奨パラメータ）を返す。
    動画はサーバーに保存されず、分析後に削除される。
    """
    for f, label in [(before, "before"), (after, "after")]:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in _PAIR_ALLOWED_EXT:
            raise HTTPException(status_code=400, detail=f"{label} の拡張子が非対応です: {ext}")

    from app.services.edit_dna import analyze_edit_pair as _analyze

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        uid = str(uuid.uuid4())[:8]

        before_ext = Path(before.filename or "").suffix.lower() or ".mp4"
        after_ext = Path(after.filename or "").suffix.lower() or ".mp4"
        before_path = tmp / f"before_{uid}{before_ext}"
        after_path = tmp / f"after_{uid}{after_ext}"

        before_path.write_bytes(await before.read())
        after_path.write_bytes(await after.read())

        try:
            result = _analyze(before_path, after_path)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"分析に失敗しました: {e}")

    return result


# ---------------------------------------------------------------------------
# Style Marketplace (Phase 6-3)
# ---------------------------------------------------------------------------

class PublishBody(BaseModel):
    public_description: str = Field("", max_length=500)
    tags: List[str] = []


class CopyProfileBody(BaseModel):
    new_name: str = Field("", max_length=80)


@router.get("/marketplace")
def get_marketplace(tag: Optional[str] = None, q: Optional[str] = None, user: dict = Depends(require_user)):
    """公開中のスタイルプロファイル一覧を返す。tag・q でフィルタリング可。"""
    return {"profiles": svc.list_public_profiles(limit=50, tag=tag, q=q)}


@router.get("/marketplace/{profile_id}")
def get_marketplace_profile(profile_id: str, user: dict = Depends(require_user)):
    profile = svc.get_public_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="公開プロファイルが見つかりません")
    return profile


@router.post("/marketplace/{profile_id}/copy")
def copy_marketplace_profile(
    profile_id: str,
    body: CopyProfileBody,
    user: dict = Depends(require_user),
):
    """公開プロファイルを自分のプロファイルとしてコピーする。"""
    try:
        profile = svc.copy_public_profile(profile_id, user["id"], body.new_name)
        if profile is None:
            raise HTTPException(status_code=500, detail="コピーに失敗しました")
        return profile
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{profile_id}/publish")
def publish_profile(profile_id: str, body: PublishBody, user: dict = Depends(require_user)):
    """プロファイルをマーケットプレイスに公開する。"""
    profile = svc.publish_profile(profile_id, user["id"], body.public_description, body.tags)
    if profile is None:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


@router.post("/{profile_id}/unpublish")
def unpublish_profile(profile_id: str, user: dict = Depends(require_user)):
    """プロファイルをマーケットプレイスから非公開にする。"""
    ok = svc.unpublish_profile(profile_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return {"unpublished": True}


class ApplyDnaBody(BaseModel):
    noise_db: float
    min_silence_seconds: float
    default_prompt: str = ""


@router.post("/{profile_id}/apply-dna")
def apply_dna(profile_id: str, body: ApplyDnaBody, user: dict = Depends(require_user)):
    """DNA 分析結果をプロファイルに適用する。"""
    profile = svc.update_profile(profile_id, user["id"], {
        "noise_db": body.noise_db,
        "min_silence_seconds": body.min_silence_seconds,
        **({"default_prompt": body.default_prompt} if body.default_prompt else {}),
    })
    if profile is None:
        raise HTTPException(status_code=404, detail="プロファイルが見つかりません")
    return profile


# ---------------------------------------------------------------------------
# Accuracy Metrics (Phase 6-2)
# ---------------------------------------------------------------------------

@router.get("/{profile_id}/accuracy")
def profile_accuracy(profile_id: str, user: dict = Depends(require_user)):
    """週ごとの accept 率推移とトレンド（improving/declining/stable）を返す。"""
    return svc.get_profile_accuracy(profile_id, user["id"])


# ---------------------------------------------------------------------------
# Marketplace Reviews (Phase 6-3)
# ---------------------------------------------------------------------------

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review_text: str = Field("", max_length=500)


@router.post("/marketplace/{profile_id}/review")
def add_marketplace_review(
    profile_id: str,
    body: ReviewCreate,
    user: dict = Depends(require_user),
):
    """公開プロファイルに星評価とレビューを投稿する（自分のプロファイルは不可）。"""
    try:
        review = svc.add_review(profile_id, user["id"], body.rating, body.review_text)
        if review is None:
            raise HTTPException(status_code=500, detail="レビューの保存に失敗しました")
        return review
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/marketplace/{profile_id}/reviews")
def get_marketplace_reviews(
    profile_id: str,
    user: dict = Depends(require_user),
):
    """公開プロファイルのレビュー一覧と統計を返す。"""
    reviews = svc.get_reviews(profile_id)
    stats = svc.get_review_stats(profile_id)
    return {"stats": stats, "reviews": reviews}
