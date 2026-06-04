import json
import shutil
import subprocess
from pathlib import Path


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


def _ffprobe() -> str:
    path = shutil.which("ffprobe")
    if path is None:
        raise RuntimeError("ffprobe not found in PATH")
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


def _has_audio(video_path: Path) -> bool:
    result = subprocess.run(
        [_ffprobe(), "-v", "quiet", "-print_format", "json",
         "-show_streams", "-select_streams", "a", str(video_path)],
        capture_output=True, text=True, timeout=30,
    )
    try:
        return len(json.loads(result.stdout).get("streams", [])) > 0
    except Exception:
        return False


def _invert_cuts(cuts: list[dict], total_duration: float) -> list[tuple[float, float]]:
    """削除区間（silence cuts）の逆：保持する区間リストを返す。"""
    sorted_cuts = sorted(cuts, key=lambda c: c["cut_start"])
    keep: list[tuple[float, float]] = []
    prev_end = 0.0

    for cut in sorted_cuts:
        start = float(cut["cut_start"])
        end = float(cut["cut_end"])
        if start > prev_end + 0.01:
            keep.append((prev_end, start))
        prev_end = max(prev_end, end)

    if prev_end < total_duration - 0.01:
        keep.append((prev_end, total_duration))

    return [(s, e) for s, e in keep if e - s > 0.05]


def render_mp4(video_path: Path, cuts: list[dict], output_path: Path) -> bool:
    """
    silence cuts を除いた MP4 を output_path に生成する。
    成功なら True、失敗なら False を返す。
    """
    ff = _ffmpeg()

    if not cuts:
        # カットなし → ストリームコピーで高速出力
        result = subprocess.run(
            [ff, "-y", "-i", str(video_path), "-c", "copy", str(output_path)],
            capture_output=True, timeout=300,
        )
        return result.returncode == 0

    duration = _get_duration(video_path)
    if duration <= 0:
        return False

    keep_segs = _invert_cuts(cuts, duration)
    if not keep_segs:
        return False

    has_audio = _has_audio(video_path)
    n = len(keep_segs)

    # filter_complex 構築
    parts: list[str] = []
    for i, (s, e) in enumerate(keep_segs):
        parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]")
        if has_audio:
            parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]")

    if has_audio:
        labels = "".join(f"[v{i}][a{i}]" for i in range(n))
        parts.append(f"{labels}concat=n={n}:v=1:a=1[outv][outa]")
        map_args = ["-map", "[outv]", "-map", "[outa]"]
        audio_args = ["-c:a", "aac", "-b:a", "128k"]
    else:
        labels = "".join(f"[v{i}]" for i in range(n))
        parts.append(f"{labels}concat=n={n}:v=1:a=0[outv]")
        map_args = ["-map", "[outv]"]
        audio_args = []

    filter_complex = ";".join(parts)

    cmd = [
        ff, "-y", "-i", str(video_path),
        "-filter_complex", filter_complex,
        *map_args,
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        *audio_args,
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
