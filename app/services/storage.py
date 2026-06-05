import os
from pathlib import Path

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "videos"
RESULTS_BUCKET = "results"
USE_CLOUD = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def _client():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


_VIDEO_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/x-m4v",
}


def upload_file(user_id: str, video_id: str, file_bytes: bytes, filename: str) -> str:
    """
    クラウドストレージにアップロードする。
    SUPABASE_ 環境変数が未設定の場合はローカルに保存してパスを返す。
    戻り値: ストレージパス（クラウド）またはローカルファイルパス
    """
    if not USE_CLOUD:
        local_path = Path("uploads") / filename
        local_path.parent.mkdir(exist_ok=True)
        local_path.write_bytes(file_bytes)
        return str(local_path)

    ext = Path(filename).suffix.lower()
    content_type = _VIDEO_CONTENT_TYPES.get(ext, "video/mp4")
    path = f"{user_id}/{video_id}/{filename}"
    _client().storage.from_(BUCKET).upload(path, file_bytes, {"content-type": content_type})
    return path


def get_local_copy(user_id: str, video_id: str, filename: str, local_dir: Path) -> Path:
    """
    クラウドからダウンロードしてローカルの一時パスに保存して返す。
    ローカル開発時はそのままローカルパスを返す。
    """
    local_path = local_dir / filename
    if not USE_CLOUD:
        return local_path

    if local_path.exists():
        return local_path

    path = f"{user_id}/{video_id}/{filename}"
    data = _client().storage.from_(BUCKET).download(path)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(data)
    return local_path


def upload_result(user_id: str, job_id: str, data: bytes, filename: str) -> str:
    """処理結果ファイル（ZIP/MP4）を results バケットにアップロードする。戻り値: ストレージパス"""
    path = f"{user_id}/{job_id}/{filename}"
    content_type = "video/mp4" if filename.endswith(".mp4") else "application/zip"
    _client().storage.from_(RESULTS_BUCKET).upload(path, data, {"content-type": content_type})
    return path


def download_result(path: str) -> bytes:
    """results バケットからファイルをダウンロードして返す。"""
    return _client().storage.from_(RESULTS_BUCKET).download(path)
