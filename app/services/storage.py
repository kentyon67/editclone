import os
from pathlib import Path

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
BUCKET = "videos"
USE_CLOUD = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def _client():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


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

    path = f"{user_id}/{video_id}/{filename}"
    _client().storage.from_(BUCKET).upload(path, file_bytes, {"content-type": "video/mp4"})
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
