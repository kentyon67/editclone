from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.middleware.auth import require_user
from app.services.analytics import log_event
from app.services.jobs import JobStatus, get_job, list_user_jobs, _jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_owned_job(job_id: str, user: dict):
    """ジョブを取得し、所有者を確認する。見つからない・権限なしの場合は 404。"""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get("")
def user_job_list(user: dict = Depends(require_user)):
    """ユーザーの最近20件のジョブ一覧（完了＋進行中）。"""
    completed = list_user_jobs(user["id"])
    completed_ids = {j.id for j in completed}

    in_progress = [
        j for j in _jobs.values()
        if j.user_id == user["id"]
        and j.status in (JobStatus.pending, JobStatus.processing)
        and j.id not in completed_ids
    ]

    combined = sorted(completed + in_progress, key=lambda j: j.created_at, reverse=True)

    return {
        "jobs": [
            {
                "job_id": j.id,
                "video_filename": j.video_path.name,
                "video_id": j.video_id,
                "status": j.status,
                "created_at": j.created_at,
                "completed_at": j.completed_at,
                "has_mp4": bool((j.result or {}).get("mp4_bytes") or (j.result or {}).get("mp4_path"))
                if j.result else False,
                "cut_count": len((j.result or {}).get("cuts") or []) if j.result else None,
            }
            for j in combined[:20]
        ]
    }


def _fetch_from_storage(path: str) -> bytes:
    from app.services.storage import download_result
    return download_result(path)


_PROGRESS_PERCENT: list[tuple[str, int]] = [
    ("完了", 100),
    ("ファイルをまとめ", 95),
    ("MP4 をレンダリング", 86),
    ("EDL", 83),
    ("Premiere XML", 80),
    ("FCPXML", 75),
    ("字幕ファイル", 70),
    ("チャプター", 65),
    ("AI", 60),
    ("無音", 50),
    ("文字起こし", 20),
    ("動画情報", 5),
]


def _calc_progress_percent(progress: str, status: str) -> int:
    if status == "completed":
        return 100
    if status == "failed":
        return 0
    for keyword, pct in _PROGRESS_PERCENT:
        if keyword in progress:
            return pct
    return 2


@router.get("/{job_id}")
def job_status(job_id: str, user: dict = Depends(require_user)):
    job = _get_owned_job(job_id, user)

    resp: dict = {
        "job_id": job.id,
        "video_id": job.video_id,
        "status": job.status,
        "progress": job.progress,
        "progress_percent": _calc_progress_percent(job.progress or "", job.status.value),
        "created_at": job.created_at,
        "completed_at": job.completed_at,
        "error": job.error,
    }

    if job.status == JobStatus.completed and job.result:
        result = job.result
        has_mp4 = bool(result.get("mp4_bytes")) or bool(result.get("mp4_path"))
        resp["result"] = {
            "info": result["info"],
            "transcript": result["transcript"],
            "cuts": result["cuts"],
            "chapters": result["chapters"],
            "youtube_description": result["youtube_description"],
            "srt": result["srt"],
            "has_mp4": has_mp4,
            "has_subtitles": result.get("has_subtitles", False),
        }

    return resp


@router.get("/{job_id}/download")
def job_download(job_id: str, user: dict = Depends(require_user)):
    """ZIP ダウンロード。"""
    job = _get_owned_job(job_id, user)
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    log_event("download_zip", video_id=job.video_id, job_id=job_id)

    zip_bytes = job.result.get("zip_bytes")
    if not zip_bytes:
        zip_path = job.result.get("zip_path", "")
        if zip_path:
            try:
                zip_bytes = _fetch_from_storage(zip_path)
            except Exception:
                pass
    if not zip_bytes:
        raise HTTPException(status_code=404, detail="ZIP file not available")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{job.video_id}_editclone.zip"'},
    )


@router.get("/{job_id}/mp4")
def job_mp4(job_id: str, user: dict = Depends(require_user)):
    """MP4 ダウンロード。"""
    job = _get_owned_job(job_id, user)
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    mp4_bytes = job.result.get("mp4_bytes")
    if not mp4_bytes:
        mp4_path = job.result.get("mp4_path", "")
        if mp4_path:
            try:
                mp4_bytes = _fetch_from_storage(mp4_path)
            except Exception:
                pass
    if not mp4_bytes:
        raise HTTPException(status_code=404, detail="MP4 not available for this job")

    log_event("download_mp4", video_id=job.video_id, job_id=job_id)
    return Response(
        content=mp4_bytes,
        media_type="video/mp4",
        headers={"Content-Disposition": f'attachment; filename="{job.video_id}_editclone.mp4"'},
    )


@router.get("/{job_id}/premiere-xml")
def job_premiere_xml(job_id: str, user: dict = Depends(require_user)):
    import io
    import zipfile

    job = _get_owned_job(job_id, user)
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    data = job.result.get("premiere_xml_bytes")
    if not data:
        # ZIP フォールバック: premiere/{stem}.xml を抽出
        zip_bytes = job.result.get("zip_bytes")
        if not zip_bytes:
            zip_path = job.result.get("zip_path", "")
            if zip_path:
                try:
                    zip_bytes = _fetch_from_storage(zip_path)
                except Exception:
                    pass
        if zip_bytes:
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
                    if xml_names:
                        data = zf.read(xml_names[0])
            except Exception:
                pass

    if not data:
        raise HTTPException(status_code=404, detail="Premiere XML not available")

    log_event("download_premiere_xml", video_id=job.video_id, job_id=job_id)
    return Response(
        content=data,
        media_type="text/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.video_id}_premiere.xml"'},
    )


@router.get("/{job_id}/edl")
def job_edl(job_id: str, user: dict = Depends(require_user)):
    import io
    import zipfile

    job = _get_owned_job(job_id, user)
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    data = job.result.get("edl_bytes")
    if not data:
        zip_bytes = job.result.get("zip_bytes")
        if not zip_bytes:
            zip_path = job.result.get("zip_path", "")
            if zip_path:
                try:
                    zip_bytes = _fetch_from_storage(zip_path)
                except Exception:
                    pass
        if zip_bytes:
            try:
                with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                    edl_names = [n for n in zf.namelist() if n.endswith(".edl")]
                    if edl_names:
                        data = zf.read(edl_names[0])
            except Exception:
                pass

    if not data:
        raise HTTPException(status_code=404, detail="EDL not available")

    log_event("download_edl", video_id=job.video_id, job_id=job_id)
    return Response(
        content=data,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.video_id}.edl"'},
    )


@router.get("/{job_id}/broll-suggestions")
def job_broll_suggestions(job_id: str, user: dict = Depends(require_user)):
    """
    完了済みジョブのトランスクリプトを分析し、B-roll挿入ポイントを提案する。
    Claude API を使用するため、ANTHROPIC_API_KEY が必要。
    """
    job = _get_owned_job(job_id, user)
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    result = job.result or {}
    transcript = result.get("transcript", {})
    segments = transcript.get("segments") or transcript.get("raw_segments") or []
    info = result.get("info", {})
    total_duration = float(info.get("duration_seconds", 0))
    prompt = getattr(job, "prompt", "") or ""

    if not segments:
        return {"job_id": job_id, "suggestions": [], "message": "トランスクリプトが見つかりません"}

    from app.services.broll import suggest_broll
    suggestions = suggest_broll(segments, prompt=prompt, total_duration=total_duration)

    log_event("broll_suggestions", user_id=user["id"], video_id=job.video_id, job_id=job_id,
              metadata={"count": len(suggestions)})

    return {
        "job_id": job_id,
        "video_id": job.video_id,
        "total_duration": total_duration,
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
    }


# ---------------------------------------------------------------------------
# Web インタラクティブ編集
# ---------------------------------------------------------------------------

class RefineRequest(BaseModel):
    prompt: str
    return_mp4: bool = True  # False にするとMP4レンダリングをスキップ（高速）


@router.post("/{job_id}/refine")
def job_refine(job_id: str, body: RefineRequest, user: dict = Depends(require_user)):
    """
    完了済みジョブに対してプロンプトで追加編集し、
    更新されたMP4・FCPXML・カットリストを返す。
    WebアプリでDaVinciチャットタブ相当のインタラクティブ編集を提供。
    """
    if not body.prompt.strip():
        raise HTTPException(400, "プロンプトを入力してください")

    from app.services.jobs import refine_job
    try:
        result = refine_job(job_id, body.prompt, user["id"])
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

    mp4_b64 = None
    if body.return_mp4 and result.get("mp4_bytes"):
        import base64
        mp4_b64 = base64.b64encode(result["mp4_bytes"]).decode()

    log_event("web_refine", user_id=user["id"], job_id=job_id,
              metadata={"prompt": body.prompt[:100], "cut_count": len(result["cuts"])})

    return {
        "job_id": job_id,
        "prompt": body.prompt,
        "operations": result["operations"],
        "cuts": result["cuts"],
        "srt": result["srt"],
        "fcpxml": result["fcpxml"],
        "mp4_base64": mp4_b64,
        "duration": result["duration"],
        "fps": result["fps"],
        "needs_fcpxml_import": result["needs_fcpxml_import"],
    }


@router.get("/{job_id}/refine/fcpxml")
def job_refine_fcpxml(job_id: str, prompt: str, user: dict = Depends(require_user)):
    """クエリパラメータのプロンプトでFCPXMLのみ即時生成（MP4なし・高速）。"""
    from app.services.jobs import refine_job
    try:
        result = refine_job(job_id, prompt, user["id"])
    except PermissionError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

    if not result["fcpxml"]:
        raise HTTPException(503, "FCPXMLの生成に失敗しました（動画ファイルが見つかりません）")

    return Response(
        content=result["fcpxml"].encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="refined_{job_id}.fcpxml"'},
    )
