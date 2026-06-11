"""
Edit DNA Extractor — 編集前後ペア動画を分析して編集スタイルを抽出する。

before: 未編集の元動画
after:  ユーザーが編集済みの完成動画

差分を解析し、カットパターン・テンポ・無音閾値を推定して Style Profile 推奨値を返す。
Whisper トランスクリプト + Claude API で詳細なスタイル分析を行う。
"""
import json
import logging
import os
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


def _transcribe_brief(video_path: Path) -> str:
    """動画を文字起こしして先頭 2000 文字を返す。Whisper が使えない場合は空文字列。"""
    try:
        from app.services.transcription import transcribe_video
        result = transcribe_video(video_path)
        segs = result.get("segments") or []
        lines = [f"{s.get('start', 0):.1f}s: {s.get('text', '').strip()}" for s in segs[:60]]
        return "\n".join(lines)[:2000]
    except Exception as e:
        logger.debug("transcribe_brief failed: %s", e)
        return ""


def _claude_analyze(
    before_transcript: str,
    after_transcript: str,
    before_dur: float,
    after_dur: float,
    removed_ratio: float,
    cuts_per_minute: float,
    avg_segment: float,
    base_prompt: str,
) -> dict:
    """
    Claude API でトランスクリプト差分を分析して詳細なスタイルインサイトを返す。
    Returns: {"suggested_prompt": str, "style_insights": list[str], "detected_operations": list[str]}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"suggested_prompt": base_prompt, "style_insights": [], "detected_operations": []}

    system = (
        "あなたは動画編集スタイル分析AIです。\n"
        "編集前後の動画トランスクリプトと統計情報を分析して、編集スタイルの特徴を抽出します。\n\n"
        "必ず以下の JSON 形式のみを返してください（前後の説明不要）:\n"
        '{"suggested_prompt": "1〜3文の編集指示", "style_insights": ["洞察1", "洞察2", ...], '
        '"detected_operations": ["cut", "trim", "speed", "subtitle", "zoom", "transition", "text", "audio", "color", "marker"]}\n\n'
        "detected_operations は元動画と編集後動画の差分から推定できる操作タイプを列挙する。\n"
        "style_insights は最大5つ。日本語で具体的に。"
    )

    before_section = f"=== 元動画トランスクリプト（先頭） ===\n{before_transcript}" if before_transcript else "（文字起こし不可）"
    after_section = f"=== 編集後トランスクリプト（先頭） ===\n{after_transcript}" if after_transcript else "（文字起こし不可）"

    user_msg = (
        f"元動画: {before_dur:.1f}秒 → 編集後: {after_dur:.1f}秒\n"
        f"削除率: {removed_ratio * 100:.1f}%  カット数/分: {cuts_per_minute}  平均セグメント: {avg_segment}秒\n\n"
        f"{before_section}\n\n"
        f"{after_section}\n\n"
        "上記の情報から編集スタイルを分析してください。"
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = resp.content[0].text.strip()
        import re
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return {
                "suggested_prompt": str(data.get("suggested_prompt") or base_prompt),
                "style_insights": [str(s) for s in (data.get("style_insights") or [])],
                "detected_operations": [str(o) for o in (data.get("detected_operations") or [])],
            }
    except Exception as e:
        logger.debug("claude_analyze failed: %s", e)

    return {"suggested_prompt": base_prompt, "style_insights": [], "detected_operations": []}


def analyze_edit_pair(before_path: Path, after_path: Path) -> dict:
    """
    編集前後ペアを分析して編集スタイル DNA を返す。

    Returns dict with:
        before_duration, after_duration, removed_ratio,
        cuts_per_minute, avg_segment_seconds,
        silence_count, detected_noise_db,
        suggested_noise_db, suggested_min_silence, suggested_prompt,
        style_insights (list[str]), detected_operations (list[str])
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

    # 統計から基本プロンプトを自動生成（Claude API が使えない場合のフォールバック）
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
    base_prompt = "。".join(parts) + "。"

    # Whisper で両動画を文字起こし（非同期で並列実行）
    before_transcript = ""
    after_transcript = ""
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_before = ex.submit(_transcribe_brief, before_path)
            f_after = ex.submit(_transcribe_brief, after_path)
            before_transcript = f_before.result(timeout=120)
            after_transcript = f_after.result(timeout=120)
    except Exception as e:
        logger.debug("parallel transcription failed: %s", e)

    # Claude API で詳細分析
    ai_result = _claude_analyze(
        before_transcript=before_transcript,
        after_transcript=after_transcript,
        before_dur=before_dur,
        after_dur=after_dur,
        removed_ratio=removed_ratio,
        cuts_per_minute=cuts_per_minute,
        avg_segment=avg_segment,
        base_prompt=base_prompt,
    )

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
        "suggested_prompt": ai_result["suggested_prompt"],
        "style_insights": ai_result["style_insights"],
        "detected_operations": ai_result["detected_operations"],
    }
