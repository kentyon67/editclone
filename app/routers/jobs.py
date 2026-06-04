import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services.analytics import log_event
from app.services.jobs import JobStatus, get_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
        resp["result"] = {
            "info": result["info"],
            "transcript": result["transcript"],
            "cuts": result["cuts"],
            "chapters": result["chapters"],
            "youtube_description": result["youtube_description"],
            "srt": result["srt"],
            "has_mp4": result.get("mp4_bytes") is not None,
        }

    return resp


@router.get("/{job_id}/download")
def job_download(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.completed:
        raise HTTPException(status_code=400, detail="Job not completed yet")

    zip_bytes = job.result["zip_bytes"]
    log_event("download_zip", video_id=job.video_id, job_id=job_id)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{job.video_id}_editclone.zip"'
        },
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
        raise HTTPException(status_code=404, detail="MP4 not available for this job")

    log_event("download_mp4", video_id=job.video_id, job_id=job_id)
    return Response(
        content=mp4_bytes,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{job.video_id}_editclone.mp4"'
        },
    )
