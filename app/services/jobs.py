import io
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path

from app.services.chapters import format_youtube_description, generate_chapters
from app.services.cut_suggestion import suggest_cuts
from app.services.fcpxml import build_fcpxml
from app.services.srt import generate_srt
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

        job.progress = "文字起こし中..."
        transcript = transcribe_video(path)

        job.progress = "無音検出中..."
        cuts = suggest_cuts(path, noise_db=job.noise_db, min_duration=job.min_duration)

        job.progress = "チャプター生成中..."
        chapters = generate_chapters(path)
        youtube_desc = format_youtube_description(chapters)

        job.progress = "字幕ファイル生成中..."
        srt_content = generate_srt(path)

        job.progress = "FCPXMLを生成中..."
        xml_content = build_fcpxml(path, noise_db=job.noise_db, min_duration=job.min_duration)

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
        }
        job.status = JobStatus.completed
        job.completed_at = datetime.utcnow().isoformat()

    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        job.completed_at = datetime.utcnow().isoformat()
