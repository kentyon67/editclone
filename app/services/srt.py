from pathlib import Path

from app.services.transcription import transcribe_video


def _srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(video_path: Path) -> str:
    result = transcribe_video(video_path)
    segments = result["segments"]

    blocks: list[str] = []
    for i, seg in enumerate(segments, 1):
        start = _srt_time(seg["start"])
        end = _srt_time(seg["end"])
        text = seg["text"].strip()
        blocks.append(f"{i}\n{start} --> {end}\n{text}")

    return "\n\n".join(blocks)
