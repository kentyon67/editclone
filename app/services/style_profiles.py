"""
Style Profile CRUD — ユーザーの編集スタイルを保存・管理する。
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _client():
    from app.services.storage import _client as storage_client
    return storage_client()


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------

def list_profiles(user_id: str) -> list[dict]:
    try:
        resp = (
            _client().table("style_profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_profiles failed: %s", e)
        return []


def get_profile(profile_id: str, user_id: str) -> Optional[dict]:
    try:
        resp = (
            _client().table("style_profiles")
            .select("*")
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_profile failed: %s", e)
        return None


def get_active_profile(user_id: str) -> Optional[dict]:
    try:
        resp = (
            _client().table("style_profiles")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_active_profile failed: %s", e)
        return None


def create_profile(user_id: str, data: dict) -> Optional[dict]:
    try:
        payload = {
            "user_id": user_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "noise_db": float(data.get("noise_db", -30.0)),
            "min_silence_seconds": float(data.get("min_silence_seconds", 0.5)),
            "default_prompt": data.get("default_prompt", ""),
            "is_active": False,
        }
        resp = _client().table("style_profiles").insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("create_profile failed: %s", e)
        return None


def update_profile(profile_id: str, user_id: str, data: dict) -> Optional[dict]:
    allowed = {"name", "description", "noise_db", "min_silence_seconds", "default_prompt"}
    payload = {k: v for k, v in data.items() if k in allowed}
    if not payload:
        return get_profile(profile_id, user_id)
    try:
        import datetime
        payload["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        resp = (
            _client().table("style_profiles")
            .update(payload)
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("update_profile failed: %s", e)
        return None


def delete_profile(profile_id: str, user_id: str) -> bool:
    try:
        _client().table("style_profiles").delete().eq("id", profile_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("delete_profile failed: %s", e)
        return False


def set_active_profile(profile_id: str, user_id: str) -> bool:
    """指定プロファイルをアクティブにし、他を非アクティブにする。"""
    try:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # 全て非アクティブ
        _client().table("style_profiles").update({"is_active": False, "updated_at": now}).eq("user_id", user_id).execute()
        # 指定プロファイルをアクティブ
        _client().table("style_profiles").update({"is_active": True, "updated_at": now}).eq("id", profile_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("set_active_profile failed: %s", e)
        return False


def increment_job_count(profile_id: str) -> None:
    try:
        resp = _client().table("style_profiles").select("job_count").eq("id", profile_id).limit(1).execute()
        if resp.data:
            current = resp.data[0].get("job_count", 0) or 0
            _client().table("style_profiles").update({"job_count": current + 1}).eq("id", profile_id).execute()
    except Exception as e:
        logger.warning("increment_job_count failed: %s", e)


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

def record_feedback(user_id: str, job_id: str, action: str, style_profile_id: Optional[str] = None, notes: str = "") -> bool:
    try:
        _client().table("feedback_logs").insert({
            "user_id": user_id,
            "job_id": job_id,
            "action": action,
            "style_profile_id": style_profile_id,
            "notes": notes,
        }).execute()
        return True
    except Exception as e:
        logger.warning("record_feedback failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Reference Videos (oEmbed only — no video download)
# ---------------------------------------------------------------------------

_OEMBED_ENDPOINTS: dict[str, str] = {
    "youtube.com": "https://www.youtube.com/oembed",
    "youtu.be": "https://www.youtube.com/oembed",
    "vimeo.com": "https://vimeo.com/api/oembed.json",
}


def _fetch_oembed(url: str) -> dict:
    """oEmbed メタ情報のみ取得。動画ダウンロードは行わない。"""
    import json
    import urllib.parse
    import urllib.request
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL は http / https のみ対応しています")

    host = parsed.netloc.replace("www.", "")
    endpoint = next(
        (ep for domain, ep in _OEMBED_ENDPOINTS.items() if domain in host),
        None,
    )
    if endpoint is None:
        raise ValueError("未対応のURLです。YouTube / Vimeo のURLのみ対応しています。")

    api_url = f"{endpoint}?url={urllib.parse.quote(url, safe='')}&format=json"
    req = urllib.request.Request(api_url, headers={"User-Agent": "EditClone/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def list_reference_videos(profile_id: str, user_id: str) -> list[dict]:
    try:
        resp = (
            _client().table("reference_videos")
            .select("*")
            .eq("style_profile_id", profile_id)
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("list_reference_videos failed: %s", e)
        return []


def add_reference_video(profile_id: str, user_id: str, url: str) -> dict:
    if not get_profile(profile_id, user_id):
        raise PermissionError("プロファイルが見つかりません")

    oembed = _fetch_oembed(url)  # raises ValueError / RuntimeError on failure

    resp = _client().table("reference_videos").insert({
        "user_id": user_id,
        "style_profile_id": profile_id,
        "url": url,
        "oembed_title": oembed.get("title"),
        "oembed_thumbnail_url": oembed.get("thumbnail_url"),
        "oembed_provider": oembed.get("provider_name"),
    }).execute()
    if not resp.data:
        raise RuntimeError("参考動画の保存に失敗しました")
    return resp.data[0]


def delete_reference_video(video_id: str, profile_id: str, user_id: str) -> bool:
    try:
        _client().table("reference_videos").delete().eq("id", video_id).eq("style_profile_id", profile_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("delete_reference_video failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# AI Profile Refinement (Phase 2)
# ---------------------------------------------------------------------------

def ai_refine_profile(profile_id: str, user_id: str) -> str:
    """フィードバック履歴と参考動画をもとに Claude がプロンプト改善を提案する。"""
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません。Railway の環境変数を確認してください。")

    profile = get_profile(profile_id, user_id)
    if profile is None:
        raise ValueError("プロファイルが見つかりません")

    # 最新フィードバック（ユーザー全体、最大15件）
    try:
        fb_resp = (
            _client().table("feedback_logs")
            .select("action, notes")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(15)
            .execute()
        )
        feedback_data = fb_resp.data or []
    except Exception:
        feedback_data = []

    # このプロファイルに紐づく参考動画
    ref_videos = list_reference_videos(profile_id, user_id)

    current_prompt = (profile.get("default_prompt") or "").strip()

    # Claude へのコンテキスト構築
    action_labels = {"accept": "満足", "partial": "まあまあ", "reject": "やり直したい"}
    feedback_lines = [
        "- " + action_labels.get(f.get("action", ""), f.get("action", ""))
        + (f": {f['notes'].strip()}" if f.get("notes", "").strip() else "")
        for f in feedback_data
    ]
    ref_lines = [
        f"- {v.get('oembed_title') or v.get('url')} ({v.get('oembed_provider') or 'unknown'})"
        for v in ref_videos
    ]

    system_prompt = (
        "あなたは動画編集AIアシスタントです。\n"
        "ユーザーの編集スタイルを分析して、AIへの編集指示プロンプトを改善します。\n\n"
        "出力ルール:\n"
        "- 改善されたプロンプト本文のみを出力すること\n"
        "- 1〜3文の日本語で簡潔に\n"
        "- 前置きや説明は一切不要\n"
        "- 例: 「冒頭の挨拶をカットしてください。言い淀み（えーと、あの）も削除してください。」"
    )

    user_message = (
        f"## 現在のプロンプト\n{current_prompt or '（未設定）'}\n\n"
        "## 参考動画（目標の編集スタイル）\n"
        + ("\n".join(ref_lines) if ref_lines else "（未設定）") + "\n\n"
        + "## 過去のフィードバック（最新順）\n"
        + ("\n".join(feedback_lines) if feedback_lines else "（フィードバックなし）") + "\n\n"
        + "上記をもとに、改善されたプロンプトを提案してください。"
    )

    try:
        import anthropic
        model = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        raise RuntimeError(f"Claude API エラー: {e}") from e
