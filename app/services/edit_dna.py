"""
Edit DNA Extractor — 編集前後ペア動画を分析して編集スタイルを抽出する。

before: 未編集の元動画
after:  ユーザーが編集済みの完成動画

差分を解析し、カットパターン・テンポ・無音閾値を推定して Style Profile 推奨値を返す。
"""
import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path is None:
        raise RuntimeError("ffprobe not found in PATH")
    return path


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


def _get_duration(video_path: Path) -> float:
    result = subprocess.run(
        [_ffprobe(), "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
        capture_output=True, text=True, timeout=30,
    )
    try:
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def _detect_silence(video_path: Path, noise_db: float = -30.0, min_dur: float = 0.3) -> list[dict]:
    """ffmpeg silencedetect で無音区間を検出する。"""
    ff = _ffmpeg()
    result = subprocess.run(
        [ff, "-i", str(video_path), "-af",
         f"silencedetect=noise={noise_db}dB:duration={min_dur}",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=120,
    )
    output = result.stderr
    silences: list[dict] = []
    start: float | None = None
    for line in output.splitlines():
        if "silence_start:" in line:
            try:
                start = float(line.split("silence_start:")[-1].strip())
            except ValueError:
                pass
        elif "silence_end:" in line and start is not None:
            parts = line.split("silence_end:")[-1].strip().split("|")
            try:
                end = float(parts[0].strip())
                silences.append({"start": start, "end": end, "duration": round(end - start, 3)})
                start = None
            except ValueError:
                pass
    return silences


def _best_silence_params(video_path: Path) -> tuple[float, list[dict]]:
    """複数の閾値で無音検出を試み、適切な件数になる閾値を返す。"""
    for noise_db in [-25.0, -30.0, -35.0, -40.0, -45.0]:
        silences = _detect_silence(video_path, noise_db)
        if 1 <= len(silences) <= 50:
            return noise_db, silences
    return -30.0, _detect_silence(video_path, -30.0)


def analyze_edit_pair(before_path: Path, after_path: Path) -> dict:
    """
    編集前後ペアを分析して編集スタイル DNA を返す。

    Returns dict with:
        before_duration, after_duration, removed_ratio,
        cuts_per_minute, avg_segment_seconds,
        silence_count, detected_noise_db,
        suggested_noise_db, suggested_min_silence, suggested_prompt
    """
    before_dur = _get_duration(before_path)
    after_dur = _get_duration(after_path)

    if before_dur <= 0 or after_dur <= 0:
        raise ValueError("動画の長さを取得できませんでした")

    if after_dur > before_dur * 1.05:
        raise ValueError("after 動画が before より長いです。順番を確認してください。")

    # after 動画の無音検出
    best_noise_db, after_silences = _best_silence_params(after_path)

    removed_ratio = max(0.0, min(1.0, (before_dur - after_dur) / before_dur))
    minutes = after_dur / 60.0 if after_dur > 0 else 1.0
    cuts_per_minute = round(len(after_silences) / minutes, 2) if after_silences else 0.0

    # after 動画の平均セグメント長（無音区間で区切った発話区間）
    if after_silences:
        gaps: list[float] = []
        prev_end = 0.0
        for s in sorted(after_silences, key=lambda x: x["start"]):
            gap = s["start"] - prev_end
            if gap > 0.1:
                gaps.append(gap)
            prev_end = s["end"]
        tail = after_dur - prev_end
        if tail > 0.1:
            gaps.append(tail)
        avg_segment = round(sum(gaps) / len(gaps), 2) if gaps else after_dur
    else:
        avg_segment = round(after_dur, 2)

    # 無音の平均長さから最小無音時間を提案
    if after_silences:
        avg_silence_dur = sum(s["duration"] for s in after_silences) / len(after_silences)
        suggested_min_silence = round(max(0.2, min(2.0, avg_silence_dur * 0.6)), 2)
    else:
        suggested_min_silence = 0.5

    suggested_noise_db = best_noise_db

    # 編集パターンからプロンプトを自動生成
    parts: list[str] = []
    if removed_ratio > 0.35:
        parts.append("冒頭の挨拶とアウトロをカットしてください")
    if removed_ratio > 0.15:
        parts.append("言い淀みや繰り返しを削除してください")
    if cuts_per_minute > 5.0:
        parts.append("テンポよく短い間もカットしてください")
    elif cuts_per_minute < 1.0 and after_silences:
        parts.append("大きな間だけをカットして話の流れを保持してください")
    if not parts:
        parts.append("無音部分をカットしてください")
    suggested_prompt = "。".join(parts) + "。"

    return {
        "before_duration": round(before_dur, 2),
        "after_duration": round(after_dur, 2),
        "removed_ratio": round(removed_ratio, 3),
        "removed_seconds": round(before_dur - after_dur, 2),
        "cuts_per_minute": cuts_per_minute,
        "avg_segment_seconds": avg_segment,
        "silence_count": len(after_silences),
        "detected_noise_db": best_noise_db,
        "suggested_noise_db": suggested_noise_db,
        "suggested_min_silence": suggested_min_silence,
        "suggested_prompt": suggested_prompt,
    }
