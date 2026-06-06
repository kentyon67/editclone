"""
Slideshow Generator — 複数枚の画像から MP4 を生成する。
"""
import shutil
import subprocess
import tempfile
from pathlib import Path


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


def create_slideshow(
    images: list[Path],
    output_path: Path,
    duration_per_slide: float = 3.0,
    fps: int = 30,
    width: int = 1920,
    height: int = 1080,
    transition: str = "fade",
) -> bool:
    """
    images リストの画像を順番に並べた MP4 を output_path に生成する。

    transition: "fade" — 0.5s クロスフェード / "none" — カット切り替え
    戻り値: 成功なら True
    """
    ff = _ffmpeg()
    if not images:
        return False

    n = len(images)
    scale_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={fps},format=yuv420p"
    )

    if transition == "fade" and n > 1:
        # 各画像を独立した入力として xfade でつなぐ
        inputs: list[str] = []
        for img in images:
            inputs += ["-loop", "1", "-t", str(duration_per_slide + 0.5), "-i", str(img)]

        filter_parts: list[str] = []
        for i in range(n):
            filter_parts.append(f"[{i}:v]{scale_filter}[v{i}]")

        # xfade チェーン
        prev = "[v0]"
        for i in range(1, n):
            offset = duration_per_slide * i - 0.5 * (i - 1)
            out = f"[xf{i}]" if i < n - 1 else "[outv]"
            filter_parts.append(
                f"{prev}[v{i}]xfade=transition=fade:duration=0.5:offset={max(0.1, offset)}{out}"
            )
            prev = f"[xf{i}]"

        filter_complex = ";".join(filter_parts)

        cmd = [
            ff, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-movflags", "+faststart",
            str(output_path),
        ]
    else:
        # concat demuxer を使用（トランジションなし or 1枚）
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            concat_file = Path(f.name)
            lines: list[str] = []
            for img in images:
                safe = str(img).replace("'", "\\'")
                lines.append(f"file '{safe}'")
                lines.append(f"duration {duration_per_slide}")
            # concat demuxer は最後の画像を再度指定する必要がある
            last = str(images[-1]).replace("'", "\\'")
            lines.append(f"file '{last}'")
            f.write("\n".join(lines))

        cmd = [
            ff, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-vf", scale_filter,
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-movflags", "+faststart",
            str(output_path),
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    finally:
        if transition != "fade" or n <= 1:
            try:
                concat_file.unlink()
            except Exception:
                pass
