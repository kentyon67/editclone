import os
from pathlib import Path

from faster_whisper import WhisperModel

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")

# モデルは初回呼び出し時に1度だけロードしてキャッシュする
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe_video(video_path: Path) -> dict:
    model = _get_model()
    segments_iter, info = model.transcribe(str(video_path), beam_size=5)

    segments = []
    full_text_parts = []
    for seg in segments_iter:
        segments.append(
            {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
            }
        )
        full_text_parts.append(seg.text)

    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration_seconds": round(info.duration, 3),
        "transcript": "".join(full_text_parts).strip(),
        "segments": segments,
    }
