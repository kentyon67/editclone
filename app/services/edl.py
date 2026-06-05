"""
CMX 3600 EDL (Edit Decision List) ジェネレーター。
DaVinci Resolve / Premiere / Avid 等が標準でインポートできる。
"""

from pathlib import Path

_NTSC_RATES = {29, 30, 60}  # drop frame 対象フレームレート（29.97 → 30 に丸め後）


def _tc_nondrop(seconds: float, fps: int) -> str:
    """秒 → SMPTE ノンドロップフレームタイムコード HH:MM:SS:FF"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    f = min(fps - 1, int(round((seconds % 1) * fps)))
    return f"{h:02d}:{m:02d}:{s:02d}:{f:02d}"


def _tc_drop(seconds: float) -> str:
    """秒 → 29.97fps ドロップフレームタイムコード HH:MM:SS;FF"""
    total = int(round(seconds * 30000 / 1001))
    fps = 30
    # ドロップフレーム計算 (SMPTE 12M)
    d = total // 17982      # 10分ブロック数
    remainder = total % 17982
    if remainder < 2:
        skip = 0
    else:
        skip = (remainder - 2) // 1798 + 1
    frame = total + 2 * (9 * d + skip)
    h = frame // (fps * 3600)
    m = (frame % (fps * 3600)) // (fps * 60)
    s = (frame % (fps * 60)) // fps
    f = frame % fps
    return f"{h:02d}:{m:02d}:{s:02d};{f:02d}"


def _tc(seconds: float, fps_raw: float) -> str:
    fps_int = int(round(fps_raw))
    # 29.97 / 59.94 など NTSC 系はドロップフレームを使用
    if fps_int in _NTSC_RATES and abs(fps_raw - fps_int) > 0.01:
        return _tc_drop(seconds)
    return _tc_nondrop(seconds, fps_int)


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
    is_drop = fps_int in _NTSC_RATES and abs(fps - fps_int) > 0.01
    kept = _kept_segments(cuts, total_duration)

    lines = [
        f"TITLE:   EditClone - {video_path.stem}",
        "FCM: DROP FRAME" if is_drop else "FCM: NON-DROP FRAME",
        "",
    ]

    rec_pos = 0.0
    for i, (src_in, src_out) in enumerate(kept, 1):
        seg_dur = src_out - src_in
        rec_in = rec_pos
        rec_out = rec_pos + seg_dur

        lines.append(
            f"{i:03d}  AX       V     C        "
            f"{_tc(src_in, fps)} {_tc(src_out, fps)} "
            f"{_tc(rec_in, fps)} {_tc(rec_out, fps)}"
        )
        lines.append(f"* FROM CLIP NAME: {video_path.name}")
        lines.append(f"* SOURCE FILE: media/{video_path.name}")
        lines.append("")

        rec_pos = rec_out

    return "\n".join(lines)
