from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.middleware.auth import require_user
from app.services.analytics import log_event
from app.services.jobs import JobStatus, get_job, list_user_jobs, _jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
def user_job_list(user: dict = Depends(require_user)):
    """ユーザーの最近20件のジョブ一覧（完了＋進行中）。"""
    completed = list_user_jobs(user["id"])
    completed_ids = {j.id for j in completed}

    # メモリ上の進行中ジョブも含める（再起動後は消えるが処理中は表示する）
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
    """Supabase Storage から results バケット経由でファイルを取得する。"""
    from app.services.storage import download_result
    return download_result(path)


@router.get("/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    resp: dict = {
        "job_id": job.id,
        "video_id": job.video_id,
        "status": job.status,
        "progress": job.progress,
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
def job_download(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
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
def job_mp4(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
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
def job_premiere_xml(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    data = job.result.get("premiere_xml_bytes")
    if not data:
        raise HTTPException(status_code=404, detail="Premiere XML not available")

    log_event("download_premiere_xml", video_id=job.video_id, job_id=job_id)
    return Response(
        content=data,
        media_type="text/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.video_id}_premiere.xml"'},
    )


@router.get("/{job_id}/edl")
def job_edl(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    data = job.result.get("edl_bytes")
    if not data:
        raise HTTPException(status_code=404, detail="EDL not available")

    log_event("download_edl", video_id=job.video_id, job_id=job_id)
    return Response(
        content=data,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.video_id}.edl"'},
    )
