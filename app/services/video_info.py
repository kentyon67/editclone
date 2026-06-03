import struct
from pathlib import Path

import cv2

UPLOAD_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".m4v"}


def find_video(video_id: str) -> Path | None:
    for ext in ALLOWED_EXTENSIONS:
        path = UPLOAD_DIR / f"{video_id}{ext}"
        if path.exists():
            return path
    return None


def _fourcc_to_str(fourcc_int: int) -> str | None:
    try:
        raw = struct.pack("<I", int(fourcc_int))
        name = raw.decode("ascii").strip("\x00")
        return name if name else None
    except Exception:
        return None


def extract_video_info(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    try:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc_int = cap.get(cv2.CAP_PROP_FOURCC)
    finally:
        cap.release()

    duration_seconds = round(frame_count / fps, 3) if fps else None

    return {
        "duration_seconds": duration_seconds,
        "width": width or None,
        "height": height or None,
        "fps": round(fps, 3) if fps else None,
        "frame_count": frame_count or None,
        "codec_name": _fourcc_to_str(fourcc_int),
    }
