"""
NLE Plugin 用 API。
Premiere UXP・FCP Extension・DaVinci Script から呼び出される。
通常の Supabase JWT 認証を使用する。
"""

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.middleware.auth import require_user
from app.services.jobs import JobStatus, get_job, list_user_jobs

router = APIRouter(prefix="/plugin", tags=["plugin"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


class TokenRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/token")
async def plugin_get_token(body: TokenRequest):
    """プラグイン用: email/password → Supabase アクセストークン"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(503, "Auth not configured")
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        resp = sb.auth.sign_in_with_password({"email": body.email, "password": body.password})
        return {"access_token": resp.session.access_token}
    except Exception:
        raise HTTPException(401, "メールアドレスまたはパスワードが正しくありません")


@router.get("/jobs")
def plugin_list_jobs(user: dict = Depends(require_user)):
    """ユーザーの完了済みジョブ一覧（プラグイン用）。"""
    jobs = list_user_jobs(user["id"])
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return {
        "jobs": [
            {
                "job_id": j.id,
                "video_id": j.video_id,
                "video_name": j.video_path.stem,
                "filename": j.video_path.name,
                "created_at": j.created_at,
                "has_mp4": j.result.get("mp4_bytes") is not None if j.result else False,
            }
            for j in jobs[:20]
        ]
    }


@router.get("/jobs/{job_id}/fcpxml")
def plugin_fcpxml(job_id: str, user: dict = Depends(require_user)):
    job = get_job(job_id)
    if not job or job.status != JobStatus.completed:
        raise HTTPException(404, "Job not found or not completed")
    result = job.result or {}
    # FCPXML は ZIP 内にあるため ZIP から取り出す
    import zipfile, io
    zip_data = result.get("zip_bytes")
    if not zip_data:
        raise HTTPException(404, "FCPXML not available")
    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".fcpxml")]
        if not names:
            raise HTTPException(404, "FCPXML not found in archive")
        content = zf.read(names[0])
    return Response(
        content=content,
        media_type="text/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.fcpxml"'},
    )


@router.get("/jobs/{job_id}/premiere-xml")
def plugin_premiere_xml(job_id: str, user: dict = Depends(require_user)):
    job = get_job(job_id)
    if not job or job.status != JobStatus.completed:
        raise HTTPException(404, "Job not found or not completed")
    data = (job.result or {}).get("premiere_xml_bytes")
    if not data:
        raise HTTPException(404, "Premiere XML not available")
    return Response(
        content=data,
        media_type="text/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_premiere.xml"'},
    )


@router.get("/jobs/{job_id}/edl")
def plugin_edl(job_id: str, user: dict = Depends(require_user)):
    job = get_job(job_id)
    if not job or job.status != JobStatus.completed:
        raise HTTPException(404, "Job not found or not completed")
    data = (job.result or {}).get("edl_bytes")
    if not data:
        raise HTTPException(404, "EDL not available")
    return Response(
        content=data,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.edl"'},
    )


@router.get("/me")
def plugin_me(user: dict = Depends(require_user)):
    """プラグインから認証確認・ユーザー情報取得に使う。"""
    return {"user_id": user["id"], "email": user.get("email", "")}
