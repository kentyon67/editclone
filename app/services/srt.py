from pathlib import Path

from app.services.transcription import transcribe_video


def _srt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = min(999, int(round((seconds % 1) * 1000)))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def segments_to_srt(segments: list[dict]) -> str:
    """セグメントリストから SRT テキストを生成する。"""
    blocks: list[str] = []
    idx = 1
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        start = _srt_time(seg["start"])
        end = _srt_time(seg["end"])
        blocks.append(f"{idx}\n{start} --> {end}\n{text}")
        idx += 1
    return "\n\n".join(blocks)


def remap_segments_for_cuts(
    segments: list[dict],
    cuts: list[dict],
    total_duration: float,
) -> list[dict]:
    """
    カット後の動画用にセグメントのタイムスタンプを再マッピングする。
    カット区間に完全に含まれるセグメントは除去する。
    またいでいるセグメントはカット境界でトリムしてタイムスタンプを調整する。
    """
    if not cuts:
        return segments

    sorted_cuts = sorted(cuts, key=lambda c: float(c["cut_start"]))

    # 保持する区間を計算
    keep_segs: list[tuple[float, float]] = []
    prev_end = 0.0
    for cut in sorted_cuts:
        cs = float(cut["cut_start"])
        ce = float(cut["cut_end"])
        if cs > prev_end + 0.01:
            keep_segs.append((prev_end, cs))
        prev_end = max(prev_end, ce)
    if prev_end < total_duration - 0.01:
        keep_segs.append((prev_end, total_duration))

    def orig_to_cut(t: float) -> float:
        """元動画の時刻をカット後動画の時刻に変換する。"""
        cut_t = 0.0
        for seg_s, seg_e in keep_segs:
            if t <= seg_s:
                return cut_t
            elif t >= seg_e:
                cut_t += seg_e - seg_s
            else:
                cut_t += t - seg_s
                return cut_t
        return cut_t

    def is_fully_cut(start: float, end: float) -> bool:
        for cut in sorted_cuts:
            cs = float(cut["cut_start"])
            ce = float(cut["cut_end"])
            if start >= cs and end <= ce:
                return True
        return False

    remapped: list[dict] = []
    for seg in segments:
        if is_fully_cut(seg["start"], seg["end"]):
            continue
        new_s = orig_to_cut(seg["start"])
        new_e = orig_to_cut(seg["end"])
        if new_e - new_s > 0.1:
            remapped.append({"start": new_s, "end": new_e, "text": seg["text"]})

    return remapped


def generate_srt(video_path: Path) -> str:
    """元動画用 SRT（編集ソフトインポート用・元のタイムスタンプ）。"""
    result = transcribe_video(video_path)
    return segments_to_srt(result["segments"])
