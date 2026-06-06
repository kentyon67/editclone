import os
from pathlib import Path

from faster_whisper import WhisperModel

# "small" は base より大幅に精度が高く、CPU でも実用的な速度で動く
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small")

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def merge_segments(
    segments: list[dict],
    max_chars: int = 40,
    max_duration: float = 5.0,
    min_gap: float = 0.6,
    lang: str = "",
) -> list[dict]:
    """
    短いWhisperセグメントを自然な字幕単位にマージする。
    lang: 言語コード。英語（en）は max_chars を 80 に拡張する。
    min_gap: この秒数以上の無音があれば必ず分割
    """
    if lang == "en" and max_chars == 40:
        max_chars = 80  # 英語は文字単位でなく単語単位なので長め
    sentence_enders = set("。！？.!?")
    merged: list[dict] = []
    cur: dict | None = None

    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue

        if cur is None:
            cur = {"start": seg["start"], "end": seg["end"], "text": text}
            continue

        gap = seg["start"] - cur["end"]
        combined = cur["text"] + text
        duration = seg["end"] - cur["start"]
        ends_sentence = cur["text"][-1] in sentence_enders if cur["text"] else False

        should_merge = (
            gap < min_gap
            and len(combined) <= max_chars
            and duration <= max_duration
            and not ends_sentence
        )

        if should_merge:
            cur["text"] = combined
            cur["end"] = seg["end"]
        else:
            merged.append(cur)
            cur = {"start": seg["start"], "end": seg["end"], "text": text}

    if cur:
        merged.append(cur)

    return merged


def transcribe_video(video_path: Path) -> dict:
    model = _get_model()
    segments_iter, info = model.transcribe(
        str(video_path),
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=True,
        no_speech_threshold=0.6,
    )

    raw_segments: list[dict] = []
    full_text_parts: list[str] = []

    for seg in segments_iter:
        text = seg.text.strip()
        if not text:
            continue
        raw_segments.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": text,
        })
        full_text_parts.append(seg.text)

    merged_segments = merge_segments(raw_segments, lang=info.language)

    sep = "" if info.language == "ja" else " "
    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration_seconds": round(info.duration, 3),
        "transcript": sep.join(p.strip() for p in full_text_parts if p.strip()),
        "segments": merged_segments,
        "raw_segments": raw_segments,
    }
