from pathlib import Path

from app.services.silence import detect_silence


def suggest_cuts(
    video_path: Path,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
) -> list[dict]:
    silence_segments = detect_silence(video_path, noise_db=noise_db, min_duration=min_duration)

    cuts = []
    for seg in silence_segments:
        if seg["silence_end"] is None:
            continue
        cuts.append({
            "cut_start": seg["silence_start"],
            "cut_end": seg["silence_end"],
            "duration": seg["duration"],
            "reason": "silence",
        })

    return cuts
