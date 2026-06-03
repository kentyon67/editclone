import re
import shutil
import subprocess
from pathlib import Path


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        raise RuntimeError("ffmpeg not found in PATH")
    return path


def detect_silence(
    video_path: Path,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
) -> list[dict]:
    cmd = [
        _ffmpeg(), "-i", str(video_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # silencedetect の出力は stderr に出る
    output = result.stderr

    starts = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", output)]
    ends   = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", output)]

    segments = []
    for i, start in enumerate(starts):
        if i < len(ends):
            end = ends[i]
            segments.append({
                "silence_start": round(start, 3),
                "silence_end":   round(end, 3),
                "duration":      round(end - start, 3),
            })
        else:
            # 動画末尾まで無音が続くケース
            segments.append({
                "silence_start": round(start, 3),
                "silence_end":   None,
                "duration":      None,
            })

    return segments
