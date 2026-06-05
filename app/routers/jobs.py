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
    return Response(
        content=job.result["zip_bytes"],
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
        headers={
            "Content-Disposition": f'attachment; filename="{job.video_id}_premiere.xml"'
        },
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
        headers={
            "Content-Disposition": f'attachment; filename="{job.video_id}.edl"'
        },
    )
