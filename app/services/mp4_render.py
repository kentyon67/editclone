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


def _hex_to_ass(hex_color: str) -> str:
    """#RRGGBB → &H00BBGGRR（ASS 字幕フォーマット、リトルエンディアン BGR）"""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"&H00{b}{g}{r}".upper()
    return "&H00FFFFFF"


def _pick_font(candidates: list[str]) -> str:
    """インストール済みフォントを候補リストから選ぶ。fc-list が使えない場合は先頭を返す。"""
    try:
        result = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=5)
        installed = result.stdout.lower()
        for font in candidates:
            if font.lower() in installed:
                return font
    except Exception:
        pass
    return candidates[0]


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


def add_subtitles_to_mp4(
    input_mp4: Path,
    srt_content: str,
    output_path: Path,
    caption_style: dict | None = None,
) -> bool:
    """
    MP4 に SRT 字幕（テロップ）を焼き込む。
    失敗した場合は False を返す（呼び出し側で無字幕 MP4 にフォールバックすること）。
    """
    if not srt_content.strip():
        return False

    ff = _ffmpeg()
    import os
    import tempfile

    srt_fd, srt_path = tempfile.mkstemp(suffix=".srt", dir=output_path.parent)
    try:
        with os.fdopen(srt_fd, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Linux パスはコロンなし。Windows 開発環境では失敗することがあるが Railway は問題なし。
        srt_escaped = str(srt_path).replace("\\", "/")
        # Windows のドライブレター（C:）があればコロンをエスケープ
        if len(srt_escaped) > 2 and srt_escaped[1] == ":":
            srt_escaped = srt_escaped[0] + "\\:" + srt_escaped[2:]

        cs = caption_style or {}
        font = _pick_font(["Noto Sans CJK JP", "Noto Sans JP", "DejaVu Sans", "Arial"])
        font_size = int(cs.get("font_size", 28))
        bold = 1 if cs.get("bold", True) else 0
        primary_color = _hex_to_ass(str(cs.get("primary_color", "#FFFFFF")))
        outline_color = _hex_to_ass(str(cs.get("outline_color", "#000000")))
        position = str(cs.get("position", "bottom"))
        alignment, margin_v = {"top": (8, 20), "middle": (5, 0)}.get(position, (2, 55))
        style = (
            f"Fontname={font},"
            f"Fontsize={font_size},"
            f"PrimaryColour={primary_color},"
            f"OutlineColour={outline_color},"
            "BorderStyle=1,"
            "Outline=3,"
            "Shadow=1,"
            f"MarginV={margin_v},"
            f"Bold={bold},"
            f"Alignment={alignment}"
        )

        cmd = [
            ff, "-y", "-i", str(input_mp4),
            "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=600)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
    finally:
        try:
            Path(srt_path).unlink()
        except Exception:
            pass


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
        # カット点のクリックノイズを防ぐため各セグメントに 20ms フェードを付ける
        faded_parts: list[str] = []
        for i, (s, e) in enumerate(keep_segs):
            seg_dur = e - s
            fade_dur = min(0.02, seg_dur / 4)  # 20ms or 1/4 of segment, whichever shorter
            parts.append(
                f"[a{i}]afade=t=in:st=0:d={fade_dur:.4f},"
                f"afade=t=out:st={max(0, seg_dur - fade_dur):.4f}:d={fade_dur:.4f}[af{i}]"
            )
            faded_parts.append(f"af{i}")
        labels = "".join(f"[v{i}][{faded_parts[i]}]" for i in range(n))
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
        "-movflags", "+faststart",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
