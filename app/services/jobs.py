import io
import logging
import tempfile
import zipfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from app.services.ai_edit import analyze_transcript_for_cuts, merge_cuts
from app.services.analytics import log_event
from app.services.chapters import format_youtube_description, generate_chapters_from_segments
from app.services.cut_suggestion import suggest_cuts
from app.services.edl import build_edl
from app.services.fcpxml import build_fcpxml
from app.services.mp4_render import add_subtitles_to_mp4, render_mp4
from app.services.premiere_xml import build_premiere_xml
from app.services.srt import remap_segments_for_cuts, segments_to_srt
from app.services.transcription import transcribe_video
from app.services.video_info import extract_video_info

logger = logging.getLogger(__name__)

_README_TEMPLATE = """\
EditClone — 自動編集パッケージ
================================

このZIPには以下のファイルが含まれています：

fcp/
  {stem}.fcpxml       — Final Cut Pro 用プロジェクト（字幕トラック付き）
                        File > Import > XML で開く
                        ※ media/ フォルダの動画を再リンクしてください

premiere/
  {stem}.xml          — Premiere Pro 用プロジェクト (XMEML)
                        File > Import で開く
                        ※ media/ フォルダの動画を再リンクしてください

davinci/
  {stem}.edl          — DaVinci Resolve 用 EDL
                        File > Import Timeline > Import EDL で開く
  ※ DaVinci Resolve 18以降では fcp/{stem}.fcpxml も直接インポート可能
     File > Import Timeline > Import XML で開く（字幕トラック付き）

subtitles/
  {stem}.srt          — 字幕ファイル (SRT)
                        YouTube / TikTok 等にアップロード可能
                        ※ DaVinci / Premiere のキャプションとしても使用可

media/
  {filename}          — 元動画（再リンク用）

chapters.txt          — YouTube チャプター（説明欄にそのまま貼り付け）

---
EditClone: https://editclone.com
"""


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Job:
    def __init__(
        self,
        video_id: str,
        video_path: Path,
        noise_db: float,
        min_duration: float,
        user_id: str = "",
        prompt: str = "",
    ):
        self.id: str = ""
        self.video_id = video_id
        self.video_path = video_path
        self.noise_db = noise_db
        self.min_duration = min_duration
        self.user_id = user_id
        self.prompt = prompt
        self.status = JobStatus.pending
        self.progress: str = ""
        self.result: dict | None = None
        self.error: str | None = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: str | None = None


_jobs: dict[str, Job] = {}


def create_job(
    video_id: str,
    video_path: Path,
    noise_db: float,
    min_duration: float,
    user_id: str = "",
    prompt: str = "",
) -> Job:
    import uuid
    job = Job(video_id, video_path, noise_db, min_duration, user_id, prompt)
    job.id = str(uuid.uuid4())
    _jobs[job.id] = job
    _insert_job_to_supabase(job)
    return job


def get_job(job_id: str) -> Job | None:
    job = _jobs.get(job_id)
    if job is not None:
        return job
    return _load_job_from_supabase(job_id)


def list_user_jobs(user_id: str) -> list[Job]:
    from app.services.storage import USE_CLOUD
    if USE_CLOUD and user_id:
        try:
            from app.services.storage import _client
            resp = (
                _client().table("jobs")
                .select("*")
                .eq("user_id", user_id)
                .in_("status", ["completed", "failed"])
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            jobs: list[Job] = []
            for data in resp.data:
                job = _reconstruct_job_from_db(data)
                _jobs[job.id] = job
                jobs.append(job)
            return jobs
        except Exception as e:
            logger.warning("Supabase list_user_jobs failed: %s", e)

    return [j for j in _jobs.values() if j.user_id == user_id and j.status == JobStatus.completed]


# ---------------------------------------------------------------------------
# Supabase persistence helpers
# ---------------------------------------------------------------------------

def _insert_job_to_supabase(job: Job) -> None:
    from app.services.storage import USE_CLOUD
    if not USE_CLOUD or not job.user_id:
        return
    try:
        from app.services.storage import _client
        _client().table("jobs").insert({
            "id": job.id,
            "user_id": job.user_id,
            "video_id": job.video_id,
            "video_filename": job.video_path.name,
            "status": "pending",
            "noise_db": job.noise_db,
            "min_duration": job.min_duration,
            "prompt": job.prompt,
        }).execute()
    except Exception as e:
        logger.warning("Supabase job insert failed: %s", e)


def _persist_to_supabase(job: Job) -> None:
    from app.services.storage import USE_CLOUD
    if not USE_CLOUD or not job.user_id:
        return
    try:
        from app.services.storage import _client, upload_result
        result = job.result or {}

        zip_path = ""
        zip_bytes = result.get("zip_bytes")
        if zip_bytes:
            try:
                zip_path = upload_result(job.user_id, job.id, zip_bytes, "project.zip")
            except Exception as e:
                logger.warning("ZIP upload failed: %s", e)

        mp4_path = ""
        mp4_bytes = result.get("mp4_bytes")
        if mp4_bytes:
            try:
                mp4_path = upload_result(job.user_id, job.id, mp4_bytes, "video.mp4")
            except Exception as e:
                logger.warning("MP4 upload failed: %s", e)

        premiere_xml_bytes = result.get("premiere_xml_bytes", b"")
        edl_bytes = result.get("edl_bytes", b"")

        metadata = {
            "info": result.get("info"),
            "transcript": result.get("transcript"),
            "cuts": result.get("cuts"),
            "chapters": result.get("chapters"),
            "youtube_description": result.get("youtube_description"),
            "srt": result.get("srt"),
            "has_mp4": mp4_bytes is not None,
            "has_subtitles": result.get("has_subtitles", False),
            "premiere_xml": premiere_xml_bytes.decode("utf-8", errors="replace") if isinstance(premiere_xml_bytes, bytes) else "",
            "edl": edl_bytes.decode("utf-8", errors="replace") if isinstance(edl_bytes, bytes) else "",
            "zip_path": zip_path,
            "mp4_path": mp4_path,
        }

        update_data: dict = {
            "status": job.status.value,
            "completed_at": job.completed_at,
            "result_metadata": metadata,
        }
        if zip_path:
            update_data["result_zip_path"] = zip_path
        if mp4_path:
            update_data["result_mp4_path"] = mp4_path
        if job.error:
            update_data["error_message"] = job.error

        _client().table("jobs").update(update_data).eq("id", job.id).execute()
    except Exception as e:
        logger.warning("Supabase job persist failed: %s", e)


def _reconstruct_job_from_db(data: dict) -> Job:
    video_filename = data.get("video_filename") or "unknown.mp4"
    job = Job(
        video_id=data["video_id"],
        video_path=Path(video_filename),
        noise_db=float(data.get("noise_db") or -30.0),
        min_duration=float(data.get("min_duration") or 0.5),
        user_id=str(data.get("user_id") or ""),
        prompt=str(data.get("prompt") or ""),
    )
    job.id = str(data["id"])
    job.status = JobStatus(data["status"])
    job.created_at = str(data.get("created_at") or "")
    completed = data.get("completed_at")
    job.completed_at = str(completed) if completed else None
    job.error = data.get("error_message")

    metadata = data.get("result_metadata") or {}
    if job.status == JobStatus.completed and metadata:
        premiere_xml_str = metadata.get("premiere_xml") or ""
        edl_str = metadata.get("edl") or ""
        job.result = {
            "info": metadata.get("info"),
            "transcript": metadata.get("transcript"),
            "cuts": metadata.get("cuts"),
            "chapters": metadata.get("chapters"),
            "youtube_description": metadata.get("youtube_description"),
            "srt": metadata.get("srt"),
            "has_mp4": metadata.get("has_mp4", False),
            "has_subtitles": metadata.get("has_subtitles", False),
            "zip_bytes": None,
            "mp4_bytes": None,
            "zip_path": metadata.get("zip_path") or data.get("result_zip_path") or "",
            "mp4_path": metadata.get("mp4_path") or data.get("result_mp4_path") or "",
            "premiere_xml_bytes": premiere_xml_str.encode("utf-8") if premiere_xml_str else b"",
            "edl_bytes": edl_str.encode("utf-8") if edl_str else b"",
        }
    return job


def _update_status_supabase(job_id: str, status: str) -> None:
    """DB のジョブステータスのみ更新する（処理開始時・失敗時の即時反映用）。"""
    from app.services.storage import USE_CLOUD
    if not USE_CLOUD:
        return
    try:
        from app.services.storage import _client
        _client().table("jobs").update({"status": status}).eq("id", job_id).execute()
    except Exception as e:
        logger.warning("Supabase status update failed: %s", e)


def _load_job_from_supabase(job_id: str) -> Job | None:
    from app.services.storage import USE_CLOUD
    if not USE_CLOUD:
        return None
    try:
        from app.services.storage import _client
        resp = _client().table("jobs").select("*").eq("id", job_id).limit(1).execute()
        if not resp.data:
            return None
        job = _reconstruct_job_from_db(resp.data[0])
        _jobs[job_id] = job
        return job
    except Exception as e:
        logger.warning("Supabase load_job failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------

def run_job(job_id: str) -> None:
    job = _jobs.get(job_id)
    if job is None:
        return

    job.status = JobStatus.processing
    _update_status_supabase(job.id, "processing")
    try:
        path = job.video_path

        # ローカルファイルがない場合（Railway 再起動後）はクラウドから復元
        if not path.exists():
            from app.services.storage import USE_CLOUD, get_local_copy
            if USE_CLOUD and job.user_id:
                try:
                    path = get_local_copy(job.user_id, job.video_id, path.name, Path("uploads"))
                    job.video_path = path
                except Exception as e:
                    logger.warning("クラウドからの動画復元に失敗: %s", e)
            if not path.exists():
                raise FileNotFoundError(f"動画ファイルが見つかりません: {path}")

        job.progress = "動画情報を取得中..."
        info = extract_video_info(path)
        total_duration = float(info.get("duration_seconds") or 0.0)
        fps = float(info.get("fps") or 30.0)
        width = int(info.get("width") or 1920)
        height = int(info.get("height") or 1080)

        job.progress = "セリフを文字起こし中..."
        transcript = transcribe_video(path)

        job.progress = "無音箇所を検出中..."
        silence_cuts = suggest_cuts(path, noise_db=job.noise_db, min_duration=job.min_duration)

        # プロンプトがあれば Claude API でセマンティックカット提案を追加
        if job.prompt:
            job.progress = "AIが編集指示を解析中..."
            ai_cuts = analyze_transcript_for_cuts(
                transcript["segments"], job.prompt, transcript["transcript"],
                total_duration=total_duration,
            )
            cuts = merge_cuts(silence_cuts, ai_cuts)
        else:
            cuts = silence_cuts

        job.progress = "チャプター生成中..."
        chapters = generate_chapters_from_segments(transcript["segments"])
        youtube_desc = format_youtube_description(chapters)

        job.progress = "字幕ファイル生成中..."
        srt_content = segments_to_srt(transcript["segments"])

        job.progress = "FCPXMLを生成中..."
        remapped_segs_for_fcpxml = remap_segments_for_cuts(
            transcript["segments"], cuts, total_duration
        )
        fcpxml_content = build_fcpxml(
            path, noise_db=job.noise_db, min_duration=job.min_duration, cuts=cuts,
            video_info=info, segments=remapped_segs_for_fcpxml,
        )

        job.progress = "Premiere XML を生成中..."
        premiere_xml_content = build_premiere_xml(
            path, cuts=cuts, total_duration=total_duration,
            fps=fps, width=width, height=height,
        )

        job.progress = "EDL を生成中..."
        edl_content = build_edl(path, cuts=cuts, total_duration=total_duration, fps=fps)

        job.progress = "MP4 をレンダリング中..."
        mp4_bytes: bytes | None = None
        has_subtitles = False

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                cut_mp4_path = tmpdir_path / f"{job.video_id}_cut.mp4"
                cut_ok = render_mp4(path, cuts, cut_mp4_path) and cut_mp4_path.exists()

                if cut_ok:
                    remapped_segs = remap_segments_for_cuts(
                        transcript["segments"], cuts, total_duration
                    )
                    srt_for_mp4 = segments_to_srt(remapped_segs)

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

        job.progress = "ファイルをまとめています..."
        stem = job.video_id
        readme = _README_TEMPLATE.format(stem=stem, filename=path.name)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.txt", readme)
            zf.writestr(f"fcp/{stem}.fcpxml", fcpxml_content)
            zf.writestr(f"premiere/{stem}.xml", premiere_xml_content)
            zf.writestr(f"davinci/{stem}.edl", edl_content)
            zf.writestr(f"subtitles/{stem}.srt", srt_content)
            zf.writestr("chapters.txt", youtube_desc)
            zf.write(path, f"media/{path.name}")
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
            "premiere_xml_bytes": premiere_xml_content.encode("utf-8"),
            "edl_bytes": edl_content.encode("utf-8"),
        }
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc).isoformat()

        log_event(
            "process_complete",
            video_id=job.video_id,
            job_id=job.id,
            metadata={
                "cut_count": len(cuts),
                "has_mp4": mp4_bytes is not None,
                "has_subtitles": has_subtitles,
                "duration_seconds": total_duration,
                "has_prompt": bool(job.prompt),
                "ai_cuts": sum(1 for c in cuts if c.get("source") in ("ai", "ai+silence")),
            },
        )

        job.progress = "完了"
        _persist_to_supabase(job)

        # Phase 3: プロジェクト自動作成
        if job.user_id:
            try:
                from app.services.projects import create_project, add_revision
                from app.services.style_profiles import get_active_profile

                active_profile = get_active_profile(job.user_id)
                project = create_project(
                    user_id=job.user_id,
                    name=job.video_path.stem,
                    source_job_id=job.id,
                    style_profile_id=active_profile["id"] if active_profile else None,
                )
                if project:
                    result_cuts = (job.result or {}).get("cuts") or []
                    add_revision(
                        project_id=project["id"],
                        user_id=job.user_id,
                        revision_number=1,
                        source="web",
                        metadata={
                            "cut_count": len(result_cuts),
                            "has_mp4": bool((job.result or {}).get("has_mp4")),
                            "prompt": job.prompt,
                            "noise_db": job.noise_db,
                            "min_duration": job.min_duration,
                        },
                    )
            except Exception as e:
                logger.warning("プロジェクト自動作成に失敗: %s", e)

    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        job.completed_at = datetime.now(timezone.utc).isoformat()
        log_event(
            "process_failed",
            video_id=job.video_id,
            job_id=job.id,
            metadata={"error": str(exc)},
        )
        _persist_to_supabase(job)
