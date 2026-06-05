"""
CMX 3600 EDL (Edit Decision List) ジェネレーター。
DaVinci Resolve / Premiere / Avid 等が標準でインポートできる。
"""

from pathlib import Path


def _tc(seconds: float, fps: int) -> str:
    """秒 → SMPTE タイムコード HH:MM:SS:FF"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    f = min(fps - 1, int(round((seconds % 1) * fps)))
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def _kept_segments(cuts: list[dict], total: float) -> list[tuple[float, float]]:
    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for cut in sorted(cuts, key=lambda c: float(c["cut_start"])):
        s, e = float(cut["cut_start"]), float(cut["cut_end"])
        if s > cursor:
            segments.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        segments.append((cursor, total))
    return [(s, e) for s, e in segments if e - s > 0.05]


def build_edl(
    video_path: Path,
    cuts: list[dict],
    total_duration: float,
    fps: float = 30.0,
) -> str:
    fps_int = int(round(fps))
    kept = _kept_segments(cuts, total_duration)

    lines = [
        f"TITLE:   EditClone - {video_path.stem}",
        "FCM: NON-DROP FRAME",
        "",
    ]

    rec_pos = 0.0
    for i, (src_in, src_out) in enumerate(kept, 1):
        seg_dur = src_out - src_in
        rec_in = rec_pos
        rec_out = rec_pos + seg_dur

        lines.append(
            f"{i:03d}  AX       V     C        "
            f"{_tc(src_in, fps_int)} {_tc(src_out, fps_int)} "
            f"{_tc(rec_in, fps_int)} {_tc(rec_out, fps_int)}"
        )
        lines.append(f"* FROM CLIP NAME: {video_path.name}")
        lines.append("")

        rec_pos = rec_out

    return "\n".join(lines)
