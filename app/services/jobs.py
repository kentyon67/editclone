import io
import tempfile
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path

from app.services.analytics import log_event
from app.services.chapters import format_youtube_description, generate_chapters_from_segments
from app.services.cut_suggestion import suggest_cuts
from app.services.fcpxml import build_fcpxml
from app.services.mp4_render import add_subtitles_to_mp4, render_mp4
from app.services.srt import remap_segments_for_cuts, segments_to_srt
from app.services.transcription import transcribe_video
from app.services.video_info import extract_video_info


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Job:
    def __init__(self, video_id: str, video_path: Path, noise_db: float, min_duration: float):
        self.id: str = ""
        self.video_id = video_id
        self.video_path = video_path
        self.noise_db = noise_db
        self.min_duration = min_duration
        self.status = JobStatus.pending
        self.progress: str = ""
        self.result: dict | None = None
        self.error: str | None = None
        self.created_at = datetime.utcnow().isoformat()
        self.completed_at: str | None = None


_jobs: dict[str, Job] = {}


def create_job(video_id: str, video_path: Path, noise_db: float, min_duration: float) -> Job:
    import uuid
    job = Job(video_id, video_path, noise_db, min_duration)
    job.id = str(uuid.uuid4())
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def run_job(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return

    job.status = JobStatus.processing
    try:
        path = job.video_path

        job.progress = "動画情報を取得中..."
        info = extract_video_info(path)
        total_duration = info.get("duration_seconds") or 0.0

        job.progress = "文字起こし中..."
        transcript = transcribe_video(path)

        job.progress = "無音検出中..."
        cuts = suggest_cuts(path, noise_db=job.noise_db, min_duration=job.min_duration)

        # チャプター・SRT・FCPXML はすべて既存結果を再利用（transcribe/silence再実行なし）
        job.progress = "チャプター生成中..."
        chapters = generate_chapters_from_segments(transcript["segments"])
        youtube_desc = format_youtube_description(chapters)

        job.progress = "字幕ファイル生成中..."
        srt_content = segments_to_srt(transcript["segments"])  # 元動画タイムスタンプ（編集ソフト用）

        job.progress = "FCPXMLを生成中..."
        xml_content = build_fcpxml(path, noise_db=job.noise_db, min_duration=job.min_duration, cuts=cuts)

        job.progress = "MP4をレンダリング中..."
        mp4_bytes: bytes | None = None
        has_subtitles = False

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Step1: 無音カット済みMP4を生成
                cut_mp4_path = tmpdir_path / f"{job.video_id}_cut.mp4"
                cut_ok = render_mp4(path, cuts, cut_mp4_path) and cut_mp4_path.exists()

                if cut_ok:
                    # Step2: カット後の動画に合わせてSRTタイムスタンプを再計算
                    remapped_segs = remap_segments_for_cuts(
                        transcript["segments"], cuts, total_duration
                    )
                    srt_for_mp4 = segments_to_srt(remapped_segs)

                    # Step3: テロップ焼き込み（失敗時は無字幕MPにフォールバック）
                    if srt_for_mp4.strip():
                        sub_mp4_path = tmpdir_path / f"{job.video_id}_sub.mp4"
                        sub_ok = (
                            add_subtitles_to_mp4(cut_mp4_path, srt_for_mp4, sub_mp4_path)
                            and sub_mp4_path.exists()
                        )
                        if sub_ok:
                            mp4_bytes = sub_mp4_path.read_bytes()
                            has_subtitles = True
                        else:
                            mp4_bytes = cut_mp4_path.read_bytes()
                    else:
                        mp4_bytes = cut_mp4_path.read_bytes()
        except Exception:
            pass

        job.progress = "ZIPにまとめています..."
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{job.video_id}.fcpxml", xml_content)
            zf.write(path, f"media/{path.name}")
            zf.writestr(f"{job.video_id}.srt", srt_content)
            zf.writestr("chapters.txt", youtube_desc)
        buf.seek(0)
        zip_bytes = buf.read()

        job.result = {
            "video_id": job.video_id,
            "info": info,
            "transcript": transcript,
            "cuts": cuts,
            "chapters": chapters,
            "youtube_description": youtube_desc,
            "srt": srt_content,
            "zip_bytes": zip_bytes,
            "mp4_bytes": mp4_bytes,
            "has_subtitles": has_subtitles,
        }
        job.status = JobStatus.completed
        job.completed_at = datetime.utcnow().isoformat()
        log_event("process_complete", video_id=job.video_id, job_id=job.id,
                  metadata={"cut_count": len(cuts), "has_mp4": mp4_bytes is not None,
                            "has_subtitles": has_subtitles,
                            "duration_seconds": total_duration})

    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        job.completed_at = datetime.utcnow().isoformat()
        log_event("process_failed", video_id=job.video_id, job_id=job.id,
                  metadata={"error": str(exc)})
