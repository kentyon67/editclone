import io
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.chapters import format_youtube_description, generate_chapters
from app.services.cut_suggestion import suggest_cuts
from app.services.fcpxml import build_fcpxml
from app.services.jobs import create_job, run_job
from app.services.silence import detect_silence
from app.services.srt import generate_srt
from app.services.transcription import transcribe_video
from app.services.video_info import extract_video_info, find_video

router = APIRouter(prefix="/videos", tags=["videos"])

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    UPLOAD_DIR.mkdir(exist_ok=True)

    video_id = str(uuid.uuid4())
    saved_name = f"{video_id}{ext}"
    save_path = UPLOAD_DIR / saved_name

    content = await file.read()
    save_path.write_bytes(content)

    return {
        "video_id": video_id,
        "filename": file.filename,
        "saved_as": saved_name,
        "path": str(save_path),
        "size_bytes": len(content),
    }


@router.get("/info/{video_id}")
def get_video_info(video_id: str):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    info = extract_video_info(path)
    return {"video_id": video_id, "filename": path.name, **info}


@router.post("/transcribe/{video_id}")
def transcribe(video_id: str):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    result = transcribe_video(path)
    return {"video_id": video_id, **result}


@router.post("/detect-silence/{video_id}")
def silence_detection(
    video_id: str,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    segments = detect_silence(path, noise_db=noise_db, min_duration=min_duration)
    return {
        "video_id": video_id,
        "noise_threshold_db": noise_db,
        "min_duration_seconds": min_duration,
        "silence_segments": segments,
    }


@router.post("/suggest-cuts/{video_id}")
def cut_suggestions(
    video_id: str,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    cuts = suggest_cuts(path, noise_db=noise_db, min_duration=min_duration)
    return {
        "video_id": video_id,
        "noise_threshold_db": noise_db,
        "min_duration_seconds": min_duration,
        "cut_count": len(cuts),
        "cuts": cuts,
    }


@router.post("/generate-fcpxml/{video_id}")
def generate_fcpxml(
    video_id: str,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    xml_content = build_fcpxml(path, noise_db=noise_db, min_duration=min_duration)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{video_id}.fcpxml", xml_content)
        zf.write(path, f"media/{path.name}")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{video_id}_editclone.zip"'},
    )


@router.post("/chapters/{video_id}")
def chapters(video_id: str):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    chapter_list = generate_chapters(path)
    youtube_desc = format_youtube_description(chapter_list)
    return {
        "video_id": video_id,
        "chapters": chapter_list,
        "youtube_description": youtube_desc,
    }


@router.post("/export-srt/{video_id}")
def export_srt(video_id: str):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    srt_content = generate_srt(path)
    return Response(
        content=srt_content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{video_id}.srt"'},
    )


@router.post("/process/{video_id}")
def process_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
):
    """全処理を非同期ジョブとして実行。job_idを即座に返す。"""
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    job = create_job(video_id, path, noise_db, min_duration)
    background_tasks.add_task(run_job, job.id)

    return {
        "job_id": job.id,
        "video_id": video_id,
        "status": job.status,
        "message": "処理を開始しました。GET /jobs/{job_id} でステータスを確認してください。",
    }
