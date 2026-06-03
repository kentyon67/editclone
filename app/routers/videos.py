import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

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
