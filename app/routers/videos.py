import io
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.services.cut_suggestion import suggest_cuts
from app.services.fcpxml import build_fcpxml
from app.services.silence import detect_silence
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
