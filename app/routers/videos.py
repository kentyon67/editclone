import io
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.middleware.auth import require_user
from app.services.analytics import log_event
from app.services.chapters import format_youtube_description, generate_chapters
from app.services.cut_suggestion import suggest_cuts
from app.services.fcpxml import build_fcpxml
from app.services.jobs import create_job, run_job
from app.services.silence import detect_silence
from app.services.srt import generate_srt
from app.services.transcription import transcribe_video
from app.services.usage import (
    DurationExceededError,
    LimitExceededError,
    check_and_increment,
    check_duration,
    get_user_plan,
)
from app.services.video_info import extract_video_info, find_video

router = APIRouter(prefix="/videos", tags=["videos"])

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    user: dict = Depends(require_user),
):
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
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) // 1024 // 1024} MB). Maximum is {MAX_UPLOAD_BYTES // 1024 // 1024} MB.",
        )
    save_path.write_bytes(content)

    # クラウドストレージにも保存（Railway 再起動後の復元用）
    from app.services.storage import USE_CLOUD, upload_file as cloud_upload
    if USE_CLOUD:
        try:
            cloud_upload(user["id"], video_id, content, saved_name)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Cloud upload failed (local copy kept): %s", e)

    log_event("upload", user_id=user["id"], video_id=video_id,
              metadata={"filename": file.filename, "size_bytes": len(content)})

    return {
        "video_id": video_id,
        "filename": file.filename,
        "saved_as": saved_name,
        "path": str(save_path),
        "size_bytes": len(content),
    }


@router.get("/info/{video_id}")
def get_video_info(video_id: str, user: dict = Depends(require_user)):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    info = extract_video_info(path)
    return {"video_id": video_id, "filename": path.name, **info}


@router.post("/transcribe/{video_id}")
def transcribe(video_id: str, user: dict = Depends(require_user)):
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
    user: dict = Depends(require_user),
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
    user: dict = Depends(require_user),
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
    user: dict = Depends(require_user),
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
def chapters(video_id: str, user: dict = Depends(require_user)):
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
def export_srt(video_id: str, user: dict = Depends(require_user)):
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    srt_content = generate_srt(path)
    return Response(
        content=srt_content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{video_id}.srt"'},
    )


@router.post("/slideshow")
async def create_slideshow(
    images: List[UploadFile] = File(..., description="画像ファイル（JPG/PNG/WEBP）"),
    duration_per_slide: float = Form(3.0, ge=0.5, le=30.0),
    transition: str = Form("fade"),
    width: int = Form(1920),
    height: int = Form(1080),
    user: dict = Depends(require_user),
):
    """
    複数枚の画像からスライドショー MP4 を生成する。
    duration_per_slide: 1枚の表示秒数（デフォルト3秒）
    transition: "fade"（クロスフェード）または "none"（カット切り替え）
    """
    allowed_img_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    for img in images:
        ext = Path(img.filename or "").suffix.lower()
        if ext not in allowed_img_ext:
            raise HTTPException(status_code=400, detail=f"非対応の画像形式: {ext}")

    if len(images) > 50:
        raise HTTPException(status_code=400, detail="画像は最大50枚まで対応しています")
    if transition not in ("fade", "none"):
        transition = "none"

    from app.services.slideshow import create_slideshow as _create

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        img_paths: list[Path] = []
        for i, img_file in enumerate(images):
            ext = Path(img_file.filename or "").suffix.lower() or ".jpg"
            dest = tmp / f"img_{i:04d}{ext}"
            dest.write_bytes(await img_file.read())
            img_paths.append(dest)

        out_path = tmp / "slideshow.mp4"
        ok = _create(
            img_paths, out_path,
            duration_per_slide=duration_per_slide,
            width=width, height=height,
            transition=transition,
        )
        if not ok or not out_path.exists():
            raise HTTPException(status_code=500, detail="スライドショーの生成に失敗しました")

        mp4_bytes = out_path.read_bytes()

    log_event("slideshow_create", user_id=user["id"], metadata={
        "image_count": len(images),
        "duration_per_slide": duration_per_slide,
        "transition": transition,
    })

    return Response(
        content=mp4_bytes,
        media_type="video/mp4",
        headers={"Content-Disposition": 'attachment; filename="slideshow.mp4"'},
    )


@router.post("/process/{video_id}")
async def process_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
    prompt: str = "",
    user: dict = Depends(require_user),
):
    """全処理を非同期ジョブとして実行。プラン制限チェック後に job_id を即座に返す。"""
    path = find_video(video_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found")

    plan = get_user_plan(user["id"])

    # 動画長チェック
    info = extract_video_info(path)
    try:
        check_duration(info.get("duration_seconds"), plan)
    except DurationExceededError as e:
        mins = lambda s: f"{int(s // 60)}分{int(s % 60)}秒"
        raise HTTPException(
            status_code=400,
            detail={
                "code": "DURATION_EXCEEDED",
                "plan": e.plan,
                "duration_seconds": e.duration,
                "max_duration_seconds": e.max_duration,
                "message": f"動画が長すぎます（{mins(e.duration)}）。{e.plan}プランの上限は{mins(e.max_duration)}です。",
            },
        )

    # 月次利用本数チェック＆インクリメント
    try:
        check_and_increment(user["id"], plan)
    except LimitExceededError as e:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "LIMIT_EXCEEDED",
                "plan": e.plan,
                "current": e.current,
                "limit": e.limit,
                "message": f"今月の処理上限に達しました（{e.current}/{e.limit}本）。アップグレードしてください。",
            },
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={"code": "USAGE_ERROR", "message": "使用回数の記録に失敗しました。もう一度お試しください。"},
        )

    job = create_job(video_id, path, noise_db, min_duration, user_id=user["id"], prompt=prompt)
    background_tasks.add_task(run_job, job.id)

    log_event("process_start", user_id=user["id"], video_id=video_id, job_id=job.id,
              metadata={"plan": plan, "duration_seconds": info.get("duration_seconds")})

    return {
        "job_id": job.id,
        "video_id": video_id,
        "status": job.status,
        "message": "処理を開始しました。GET /jobs/{job_id} でステータスを確認してください。",
    }
