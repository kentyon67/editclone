from pathlib import Path

from app.services.transcription import transcribe_video

_MIN_CHAPTER_SEC = 30.0
_GAP_SEC = 3.0


def _fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def generate_chapters(video_path: Path) -> list[dict]:
    result = transcribe_video(video_path)
    segments = result["segments"]
    if not segments:
        return [{"start_seconds": 0.0, "start_formatted": "0:00", "title": "Start"}]

    chapters: list[dict] = []
    chapter_start = segments[0]["start"]
    buf: list[str] = []

    for i, seg in enumerate(segments):
        buf.append(seg["text"].strip())
        is_last = i == len(segments) - 1
        next_gap = (
            not is_last
            and (segments[i + 1]["start"] - seg["end"]) >= _GAP_SEC
        )
        elapsed = seg["end"] - chapter_start

        if (next_gap and elapsed >= _MIN_CHAPTER_SEC) or is_last:
            title = " ".join(buf)[:60].strip()
            chapters.append(
                {
                    "start_seconds": round(chapter_start, 3),
                    "start_formatted": _fmt(chapter_start),
                    "title": title,
                }
            )
            if not is_last:
                chapter_start = segments[i + 1]["start"]
                buf = []

    return chapters


def format_youtube_description(chapters: list[dict]) -> str:
    return "\n".join(f"{c['start_formatted']} {c['title']}" for c in chapters)
