"""
NLE Plugin 用 API。
Premiere UXP・FCP Extension・DaVinci Script から呼び出される。
通常の Supabase JWT 認証を使用する。
"""

import os
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.middleware.auth import require_user
from app.services.jobs import JobStatus, create_job, get_job, list_user_jobs, run_job

router = APIRouter(prefix="/plugin", tags=["plugin"])

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


class TokenRequest(BaseModel):
    email: str
    password: str


class AgentEditRequest(BaseModel):
    prompt: str
    style_profile_id: Optional[str] = None


class ChatEditRequest(BaseModel):
    prompt: str
    history: list = []


class RichFcpxmlRequest(BaseModel):
    operations: list = []


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

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


@router.get("/me")
def plugin_me(user: dict = Depends(require_user)):
    """プラグインから認証確認・ユーザー情報取得に使う。"""
    return {"user_id": user["id"], "email": user.get("email", "")}


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

@router.get("/jobs")
def plugin_list_jobs(user: dict = Depends(require_user)):
    """ユーザーの完了済みジョブ一覧（プラグイン用）。"""
    all_jobs = list_user_jobs(user["id"])
    completed = [j for j in all_jobs if j.status == JobStatus.completed]
    completed.sort(key=lambda j: j.created_at, reverse=True)
    return {
        "jobs": [
            {
                "job_id": j.id,
                "video_id": j.video_id,
                "video_name": j.video_path.stem,
                "filename": j.video_path.name,
                "created_at": j.created_at,
                "has_mp4": bool(
                    (j.result.get("mp4_bytes") or j.result.get("mp4_path"))
                    if j.result else False
                ),
                "cut_count": len((j.result or {}).get("cuts") or []),
                "prompt": j.prompt or "",
            }
            for j in completed[:20]
        ]
    }


@router.get("/jobs/{job_id}/poll")
def plugin_poll_job(job_id: str, user: dict = Depends(require_user)):
    """ジョブのステータスをポーリング（プラグイン用）。"""
    job = get_job(job_id)
    if not job or job.user_id != user["id"]:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.id,
        "status": job.status.value,
        "progress": job.progress or "",
        "error": job.error,
    }


@router.get("/jobs/{job_id}/details")
def plugin_job_details(job_id: str, user: dict = Depends(require_user)):
    """ジョブの詳細（トランスクリプト・カット一覧・プロジェクトID）を返す。"""
    job = get_job(job_id)
    if not job or job.user_id != user["id"]:
        raise HTTPException(404, "Job not found")
    result = job.result or {}
    info = result.get("info") or {}
    cuts = result.get("cuts") or []
    transcript = result.get("transcript") or {}
    segments = transcript.get("segments", []) if isinstance(transcript, dict) else []

    # プロジェクト ID を source_job_id で逆引き
    project_id: Optional[str] = None
    try:
        from app.services.storage import USE_CLOUD, _client
        if USE_CLOUD:
            resp = (
                _client().table("projects")
                .select("id")
                .eq("source_job_id", job_id)
                .limit(1)
                .execute()
            )
            if resp.data:
                project_id = resp.data[0]["id"]
    except Exception:
        pass

    # SRT の存在確認: result 直接 or ZIP 内
    srt_available = bool(result.get("srt"))
    if not srt_available:
        import io
        import zipfile
        zip_data = result.get("zip_bytes")
        if not zip_data and result.get("zip_path"):
            try:
                from app.services.storage import download_result
                zip_data = download_result(result["zip_path"])
            except Exception:
                pass
        if zip_data:
            try:
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    srt_available = any(n.endswith(".srt") for n in zf.namelist())
            except Exception:
                pass

    return {
        "job_id": job.id,
        "video_name": job.video_path.stem,
        "filename": job.video_path.name,
        "status": job.status.value,
        "progress": job.progress or "",
        "created_at": job.created_at,
        "prompt": job.prompt or "",
        "duration": float(info.get("duration_seconds", 0)),
        "fps": float(info.get("fps", 30)),
        "cut_count": len(cuts),
        "cuts": cuts,
        "segments": segments[:100],
        "has_mp4": bool(result.get("mp4_bytes") or result.get("mp4_path")),
        "srt_available": srt_available,
        "project_id": project_id,
        "chapters": result.get("chapters") or [],
    }


@router.post("/jobs/{job_id}/agent-edit")
def plugin_agent_edit(
    job_id: str,
    body: AgentEditRequest,
    user: dict = Depends(require_user),
):
    """プラグインから AI エージェント編集を開始する。新しいジョブ ID を返す。"""
    job = get_job(job_id)
    if not job or job.user_id != user["id"]:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.completed:
        raise HTTPException(400, "元ジョブが完了していません")

    new_job_id: Optional[str] = None

    # プロジェクト経由で再エクスポート（存在する場合）
    try:
        from app.services.storage import USE_CLOUD, _client as sc
        if USE_CLOUD:
            resp = (
                sc().table("projects")
                .select("id")
                .eq("source_job_id", job_id)
                .limit(1)
                .execute()
            )
            if resp.data:
                project_id = resp.data[0]["id"]
                from app.services.projects import re_export_project
                new_job_id = re_export_project(project_id, user["id"], body.prompt)
    except Exception:
        pass

    # プロジェクトなし or 失敗: 直接新規ジョブ作成
    if not new_job_id:
        new_job = create_job(
            video_id=job.video_id,
            video_path=job.video_path,
            noise_db=job.noise_db,
            min_duration=job.min_duration,
            user_id=user["id"],
            prompt=body.prompt,
        )
        new_job_id = new_job.id

    threading.Thread(target=run_job, args=(new_job_id,), daemon=True).start()
    return {"job_id": new_job_id, "message": "AI 編集を開始しました"}


# ---------------------------------------------------------------------------
# Style Profiles
# ---------------------------------------------------------------------------

@router.get("/style-profiles")
def plugin_style_profiles(user: dict = Depends(require_user)):
    """ユーザーのスタイルプロファイル一覧（プラグイン用）。"""
    from app.services.style_profiles import list_profiles
    return {"profiles": list_profiles(user["id"])}


@router.post("/style-profiles/{profile_id}/activate")
def plugin_activate_profile(profile_id: str, user: dict = Depends(require_user)):
    """スタイルプロファイルをアクティブに設定し、他を非アクティブにする。"""
    from app.services import style_profiles as sp
    profiles = sp.list_profiles(user["id"])
    for p in profiles:
        if p["id"] != profile_id and p.get("is_active"):
            sp.update_profile(p["id"], user["id"], {"is_active": False})
    updated = sp.update_profile(profile_id, user["id"], {"is_active": True})
    if updated is None:
        raise HTTPException(404, "プロファイルが見つかりません")
    return updated


# ---------------------------------------------------------------------------
# File downloads
# ---------------------------------------------------------------------------

def _load_zip(job_id: str) -> Optional[bytes]:
    """ZIP データをメモリまたは Supabase Storage から取得する。"""
    import io
    import zipfile

    job = get_job(job_id)
    if not job or job.status != JobStatus.completed:
        return None
    result = job.result or {}
    zip_data = result.get("zip_bytes")
    if zip_data:
        return zip_data
    zip_path = result.get("zip_path", "")
    if zip_path:
        try:
            from app.services.storage import download_result
            return download_result(zip_path)
        except Exception:
            pass
    return None


@router.get("/jobs/{job_id}/fcpxml")
def plugin_fcpxml(job_id: str, user: dict = Depends(require_user)):
    import io
    import zipfile

    job = get_job(job_id)
    if not job or job.user_id != user["id"] or job.status != JobStatus.completed:
        raise HTTPException(404, "Job not found or not completed")

    zip_data = _load_zip(job_id)
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
    if not job or job.user_id != user["id"] or job.status != JobStatus.completed:
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
    if not job or job.user_id != user["id"] or job.status != JobStatus.completed:
        raise HTTPException(404, "Job not found or not completed")
    data = (job.result or {}).get("edl_bytes")
    if not data:
        raise HTTPException(404, "EDL not available")
    return Response(
        content=data,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.edl"'},
    )


@router.get("/jobs/{job_id}/srt")
def plugin_srt(job_id: str, user: dict = Depends(require_user)):
    """SRT 字幕ファイルを返す（プラグイン用）。"""
    import io
    import zipfile

    job = get_job(job_id)
    if not job or job.user_id != user["id"] or job.status != JobStatus.completed:
        raise HTTPException(404, "Job not found or not completed")
    result = job.result or {}

    # result に直接あるケース
    srt_data = result.get("srt")
    if not srt_data:
        zip_data = _load_zip(job_id)
        if zip_data:
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                srt_names = [n for n in zf.namelist() if n.endswith(".srt")]
                if srt_names:
                    srt_data = zf.read(srt_names[0]).decode("utf-8")

    if not srt_data:
        raise HTTPException(404, "SRT not available")
    content = srt_data if isinstance(srt_data, bytes) else srt_data.encode("utf-8")
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job_id}.srt"'},
    )


# ---------------------------------------------------------------------------
# Interactive (chat) editing
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/chat-edit")
def plugin_chat_edit(
    job_id: str,
    body: ChatEditRequest,
    user: dict = Depends(require_user),
):
    """
    プロンプトを AI で解析して DaVinci 向け編集操作リストを即時返す。
    新規ジョブを作らずトランスクリプトを再利用するため高速。
    """
    job = get_job(job_id)
    if not job or job.user_id != user["id"]:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.completed:
        raise HTTPException(400, "Job not completed yet")

    result = job.result or {}
    transcript = result.get("transcript") or {}
    current_cuts = result.get("cuts") or []
    info = result.get("info") or {}
    fps = float(info.get("fps", 30))
    duration = float(info.get("duration_seconds", 0))

    from app.services.interactive_edit import parse_edit_prompt
    operations = parse_edit_prompt(
        prompt=body.prompt,
        transcript=transcript,
        current_cuts=current_cuts,
        duration=duration,
        fps=fps,
        history=body.history,
    )

    # DaVinci Python API 非対応の操作があれば通知
    needs_fcpxml = any(
        op.get("type") in ("speed", "transition", "text", "color")
        for op in operations
    )
    return {
        "operations": operations,
        "job_id": job_id,
        "fps": fps,
        "duration": duration,
        "srt_available": bool(result.get("srt")),
        "needs_fcpxml_import": needs_fcpxml,
    }


@router.post("/jobs/{job_id}/rich-fcpxml")
def plugin_rich_fcpxml(
    job_id: str,
    body: RichFcpxmlRequest,
    user: dict = Depends(require_user),
):
    """
    操作リストを受け取りリッチ FCPXML を生成して返す。
    DaVinci で Python API 非対応の操作（速度・トランジション・テキスト等）を
    FCPXML インポートで適用するために使う。
    """
    import io
    import zipfile

    job = get_job(job_id)
    if not job or job.user_id != user["id"]:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.completed:
        raise HTTPException(400, "Job not completed yet")

    result = job.result or {}
    info = result.get("info") or {}
    cuts = result.get("cuts") or []
    transcript = result.get("transcript") or {}
    segments_raw = transcript.get("segments", []) if isinstance(transcript, dict) else []

    from app.services.fcpxml import build_fcpxml
    from app.services.srt import remap_segments_for_cuts

    total_dur = float(info.get("duration_seconds", 0))
    fps = float(info.get("fps", 30))

    remapped = remap_segments_for_cuts(segments_raw, cuts, total_dur)
    fcpxml_content = build_fcpxml(
        job.video_path,
        cuts=cuts,
        video_info=info,
        segments=remapped,
        operations=body.operations,
    )
    return Response(
        content=fcpxml_content.encode("utf-8"),
        media_type="text/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job_id}_rich.fcpxml"'},
    )
