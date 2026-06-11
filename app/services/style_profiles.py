"""
Style Profile CRUD + Marketplace — ユーザーの編集スタイルを保存・管理・公開する。
"""
import datetime
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


_DEFAULT_CAPTION_STYLE = {
    "font_size": 28,
    "position": "bottom",
    "primary_color": "#FFFFFF",
    "outline_color": "#000000",
    "bold": True,
}


def create_profile(user_id: str, data: dict) -> Optional[dict]:
    try:
        payload = {
            "user_id": user_id,
            "name": data["name"],
            "description": data.get("description", ""),
            "noise_db": float(data.get("noise_db", -30.0)),
            "min_silence_seconds": float(data.get("min_silence_seconds", 0.5)),
            "default_prompt": data.get("default_prompt", ""),
            "caption_style": data.get("caption_style") or _DEFAULT_CAPTION_STYLE,
            "is_active": False,
        }
        resp = _client().table("style_profiles").insert(payload).execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("create_profile failed: %s", e)
        return None


def update_profile(profile_id: str, user_id: str, data: dict) -> Optional[dict]:
    allowed = {"name", "description", "noise_db", "min_silence_seconds", "default_prompt", "caption_style",
               "is_public", "public_description", "tags"}
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

def get_profile_stats(profile_id: str, user_id: str) -> dict:
    """プロファイルのフィードバック統計を返す。"""
    try:
        resp = (
            _client().table("feedback_logs")
            .select("action")
            .eq("user_id", user_id)
            .eq("style_profile_id", profile_id)
            .execute()
        )
        rows = resp.data or []
        counts: dict[str, int] = {"accept": 0, "partial": 0, "reject": 0}
        for row in rows:
            a = row.get("action", "")
            if a in counts:
                counts[a] += 1
        return {"total": len(rows), **counts}
    except Exception as e:
        logger.warning("get_profile_stats failed: %s", e)
        return {"total": 0, "accept": 0, "partial": 0, "reject": 0}


def record_feedback(user_id: str, job_id: str, action: str, style_profile_id: Optional[str] = None, notes: str = "") -> bool:
    try:
        _client().table("feedback_logs").insert({
            "user_id": user_id,
            "job_id": job_id,
            "action": action,
            "style_profile_id": style_profile_id,
            "notes": notes,
        }).execute()

        # フィードバックが 5 件ごとに自動でプロンプトを改善する
        if style_profile_id:
            try:
                resp = (
                    _client().table("feedback_logs")
                    .select("id", count="exact")
                    .eq("user_id", user_id)
                    .eq("style_profile_id", style_profile_id)
                    .execute()
                )
                total = (resp.count or 0)
                if total > 0 and total % 5 == 0:
                    _auto_refine_profile(style_profile_id, user_id)
            except Exception as e:
                logger.debug("auto-refine check failed: %s", e)

        return True
    except Exception as e:
        logger.warning("record_feedback failed: %s", e)
        return False


def record_prompt_pattern(
    profile_id: str,
    user_id: str,
    prompt: str,
    operation_types: list[str],
) -> None:
    """
    チャット編集のプロンプト→操作タイプのマッピングをプロファイルに蓄積する。
    prompt_patterns カラム（JSONB 配列）に追記し、10件ごとに auto-refine を実施する。
    カラムが存在しない古いプロファイルも graceful に処理する。
    """
    try:
        import datetime
        import json

        profile = get_profile(profile_id, user_id)
        if not profile:
            return

        # 既存パターン取得（カラムがない場合は []）
        patterns: list[dict] = profile.get("prompt_patterns") or []
        if not isinstance(patterns, list):
            patterns = []

        # 既存の同一プロンプトがあればカウントアップ、なければ新規追加
        matched = next((p for p in patterns if p.get("prompt") == prompt), None)
        if matched:
            matched["count"] = matched.get("count", 1) + 1
            matched["operation_types"] = operation_types
        else:
            patterns.append({
                "prompt": prompt,
                "operation_types": operation_types,
                "count": 1,
            })

        # 最大 50 件（古いものから削除）
        if len(patterns) > 50:
            patterns = sorted(patterns, key=lambda p: p.get("count", 1), reverse=True)[:50]

        _client().table("style_profiles").update({
            "prompt_patterns": patterns,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("id", profile_id).eq("user_id", user_id).execute()

        # 10 件ごとに自動改善トリガー
        if len(patterns) % 10 == 0:
            _auto_refine_profile(profile_id, user_id)

    except Exception as e:
        logger.debug("record_prompt_pattern failed: %s", e)


def _auto_refine_profile(profile_id: str, user_id: str) -> None:
    """フィードバック蓄積時に自動でプロンプトを改善して default_prompt を更新する。"""
    try:
        suggested = ai_refine_profile(profile_id, user_id)
        if suggested:
            import datetime
            _client().table("style_profiles").update({
                "default_prompt": suggested,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }).eq("id", profile_id).eq("user_id", user_id).execute()
            logger.info("auto-refined profile %s for user %s", profile_id, user_id)
    except Exception as e:
        logger.debug("auto-refine failed: %s", e)


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


def add_reference_video_from_file(
    profile_id: str,
    user_id: str,
    file_path,  # Path object to an uploaded temp file
    original_filename: str,
) -> dict:
    """
    ユーザーが自身で権利を持つ動画ファイルを参考動画として登録する。
    Whisper で文字起こし + Claude でスタイル分析してインサイトを保存する。
    動画ファイル自体はサーバーに保存しない（分析後に削除）。
    """
    if not get_profile(profile_id, user_id):
        raise PermissionError("プロファイルが見つかりません")

    # Whisper 文字起こし（失敗しても続行）
    transcript_text = ""
    transcript_preview = ""
    try:
        from app.services.transcription import transcribe_video
        result = transcribe_video(file_path)
        segs = result.get("segments") or []
        lines = [f"{s.get('start', 0):.1f}s: {s.get('text', '').strip()}" for s in segs[:60]]
        transcript_preview = "\n".join(lines)[:2000]
        transcript_text = (result.get("transcript") or "")[:500]
    except Exception as e:
        logger.debug("transcription failed for ref video: %s", e)

    # Claude でスタイルインサイトを生成
    analysis_summary = ""
    try:
        import os, anthropic as _ant
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if api_key and transcript_preview:
            client = _ant.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                system=(
                    "あなたは動画編集スタイル分析AIです。\n"
                    "トランスクリプトから動画の編集スタイル・テンポ・特徴を3つ以内で箇条書きにしてください。\n"
                    "日本語で簡潔に。前置き不要。"
                ),
                messages=[{
                    "role": "user",
                    "content": f"ファイル名: {original_filename}\n\n=== トランスクリプト ===\n{transcript_preview}",
                }],
            )
            analysis_summary = resp.content[0].text.strip()
    except Exception as e:
        logger.debug("claude analysis failed for ref video: %s", e)

    resp = _client().table("reference_videos").insert({
        "user_id": user_id,
        "style_profile_id": profile_id,
        "url": f"file://{original_filename}",
        "oembed_title": original_filename,
        "oembed_thumbnail_url": None,
        "oembed_provider": "upload",
        "analysis_summary": analysis_summary or None,
        "transcript_preview": transcript_text or None,
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

# ---------------------------------------------------------------------------
# Style Marketplace (Phase 6-3)
# ---------------------------------------------------------------------------

_MARKETPLACE_SELECT = (
    "id,name,description,public_description,noise_db,min_silence_seconds,"
    "default_prompt,caption_style,copy_count,tags,user_id,created_at"
)

_VALID_TAGS = {
    "YouTube", "TikTok", "Podcast", "Interview", "Tutorial",
    "Vlog", "Talk", "Documentary", "SNS", "Business",
}


def list_public_profiles(limit: int = 30, tag: Optional[str] = None, q: Optional[str] = None) -> list[dict]:
    """公開中のスタイルプロファイルを人気順（copy_count降順）で返す。q でキーワード絞り込み。"""
    try:
        query = (
            _client().table("style_profiles")
            .select(_MARKETPLACE_SELECT)
            .eq("is_public", True)
            .order("copy_count", desc=True)
            .limit(limit)
        )
        if tag and tag in _VALID_TAGS:
            query = query.contains("tags", [tag])
        rows: list[dict] = query.execute().data or []
        # キーワード絞り込み（name / description / tags をクライアントサイドでフィルタ）
        if q:
            q_lower = q.lower()
            rows = [
                r for r in rows
                if q_lower in (r.get("name") or "").lower()
                or q_lower in (r.get("public_description") or "").lower()
                or any(q_lower in t.lower() for t in (r.get("tags") or []))
            ]
        return rows
    except Exception as e:
        logger.warning("list_public_profiles failed: %s", e)
        return []


def get_public_profile(profile_id: str) -> Optional[dict]:
    """公開プロファイルを1件取得する（誰でも閲覧可能）。"""
    try:
        resp = (
            _client().table("style_profiles")
            .select(_MARKETPLACE_SELECT)
            .eq("id", profile_id)
            .eq("is_public", True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("get_public_profile failed: %s", e)
        return None


def publish_profile(profile_id: str, user_id: str, public_description: str = "", tags: list[str] | None = None) -> Optional[dict]:
    """プロファイルをマーケットプレイスに公開する。"""
    safe_tags = [t for t in (tags or []) if t in _VALID_TAGS]
    try:
        resp = (
            _client().table("style_profiles")
            .update({
                "is_public": True,
                "public_description": public_description[:500],
                "tags": safe_tags,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })
            .eq("id", profile_id)
            .eq("user_id", user_id)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("publish_profile failed: %s", e)
        return None


def unpublish_profile(profile_id: str, user_id: str) -> bool:
    """プロファイルをマーケットプレイスから非公開にする。"""
    try:
        _client().table("style_profiles").update({
            "is_public": False,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }).eq("id", profile_id).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.warning("unpublish_profile failed: %s", e)
        return False


def copy_public_profile(source_id: str, user_id: str, new_name: str = "") -> Optional[dict]:
    """公開プロファイルを自分のプロファイルとしてコピーする。"""
    source = get_public_profile(source_id)
    if source is None:
        raise ValueError("公開プロファイルが見つかりません")

    name = new_name.strip() or f"{source['name']} (コピー)"
    new_profile = create_profile(user_id, {
        "name": name[:80],
        "description": source.get("description", ""),
        "noise_db": source.get("noise_db", -30.0),
        "min_silence_seconds": source.get("min_silence_seconds", 0.5),
        "default_prompt": source.get("default_prompt", ""),
        "caption_style": source.get("caption_style"),
    })

    # copy_count を原子的にインクリメント
    try:
        current = int(source.get("copy_count") or 0)
        _client().table("style_profiles").update(
            {"copy_count": current + 1}
        ).eq("id", source_id).execute()
    except Exception:
        pass

    return new_profile


def ai_refine_profile(profile_id: str, user_id: str) -> str:
    """フィードバック履歴・参考動画・プロンプトパターンをもとに Claude がプロンプト改善を提案する。"""
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

    # プロンプトパターン（チャット編集で蓄積したプロンプト→操作タイプのマッピング）
    prompt_patterns: list[dict] = []
    if isinstance(profile.get("prompt_patterns"), list):
        # 使用回数の多い順・上位15件
        prompt_patterns = sorted(
            profile["prompt_patterns"], key=lambda p: p.get("count", 1), reverse=True
        )[:15]

    current_prompt = (profile.get("default_prompt") or "").strip()

    # Claude へのコンテキスト構築
    action_labels = {"accept": "満足", "partial": "まあまあ", "reject": "やり直したい"}
    feedback_lines = [
        "- " + action_labels.get(f.get("action", ""), f.get("action", ""))
        + (f": {f['notes'].strip()}" if f.get("notes", "").strip() else "")
        for f in feedback_data
        if not str(f.get("notes", "")).startswith("auto:")  # 自動記録は除外
    ]
    ref_lines = []
    for v in ref_videos:
        title = v.get("oembed_title") or v.get("url") or ""
        provider = v.get("oembed_provider") or "unknown"
        summary = v.get("analysis_summary", "")
        line = f"- {title} ({provider})"
        if summary:
            line += f"\n  分析: {summary}"
        ref_lines.append(line)

    op_label_map = {
        "cut": "カット", "trim": "トリム", "speed": "速度変更", "subtitle": "字幕",
        "zoom": "ズーム", "transition": "トランジション", "text": "テキスト",
        "audio": "音量", "color": "カラー", "marker": "マーカー", "bgm": "BGM",
    }
    pattern_lines = []
    for p in prompt_patterns:
        ops = [op_label_map.get(t, t) for t in (p.get("operation_types") or [])]
        ops_str = "・".join(ops) if ops else "不明"
        count = p.get("count", 1)
        pattern_lines.append(f'- 「{p.get("prompt", "")}」→ [{ops_str}]（{count}回使用）')

    system_prompt = (
        "あなたは動画編集AIアシスタントです。\n"
        "ユーザーの編集スタイルを分析して、AIへの編集指示プロンプトを改善します。\n\n"
        "出力ルール:\n"
        "- 改善されたプロンプト本文のみを出力すること\n"
        "- 1〜3文の日本語で簡潔に\n"
        "- 前置きや説明は一切不要\n"
        "- プロンプトパターンに頻出する操作タイプを優先して組み込むこと\n"
        "- 例: 「冒頭の挨拶をカットしてください。言い淀み（えーと、あの）も削除してください。」"
    )

    user_message = (
        f"## 現在のプロンプト\n{current_prompt or '（未設定）'}\n\n"
        "## 参考動画（目標の編集スタイル）\n"
        + ("\n".join(ref_lines) if ref_lines else "（未設定）") + "\n\n"
        + "## よく使うチャット編集指示（実績データ）\n"
        + ("\n".join(pattern_lines) if pattern_lines else "（データなし）") + "\n\n"
        + "## 過去のフィードバック（最新順）\n"
        + ("\n".join(feedback_lines) if feedback_lines else "（フィードバックなし）") + "\n\n"
        + "上記のチャット編集パターンとフィードバックをもとに、より精度の高い改善されたプロンプトを提案してください。"
    )

    try:
        import anthropic
        model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
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


# ---------------------------------------------------------------------------
# Accuracy Metrics (Phase 6-2: パーソナライズ精度の定量評価)
# ---------------------------------------------------------------------------

def get_profile_accuracy(profile_id: str, user_id: str) -> dict:
    """
    プロファイルのパーソナライズ精度を時系列で評価する。
    週ごとのaccept率推移と、トレンド（改善中/低下中/安定）を返す。
    """
    try:
        resp = (
            _client().table("feedback_logs")
            .select("action, created_at")
            .eq("user_id", user_id)
            .eq("style_profile_id", profile_id)
            .order("created_at", desc=False)
            .execute()
        )
        rows = resp.data or []
    except Exception as e:
        logger.warning("get_profile_accuracy failed: %s", e)
        return _empty_accuracy()

    if not rows:
        return _empty_accuracy()

    # 週ごとに集計
    from collections import defaultdict
    weekly: dict[str, dict] = defaultdict(lambda: {"accept": 0, "partial": 0, "reject": 0, "total": 0})
    for row in rows:
        created = row.get("created_at", "")
        week = _iso_week_key(created)
        action = row.get("action", "")
        weekly[week]["total"] += 1
        if action in ("accept", "partial", "reject"):
            weekly[week][action] += 1

    sorted_weeks = sorted(weekly.keys())
    week_data = []
    for w in sorted_weeks:
        d = weekly[w]
        total = d["total"]
        accept_rate = round((d["accept"] + d["partial"] * 0.5) / total, 3) if total > 0 else 0
        week_data.append({
            "week": w,
            "accept": d["accept"],
            "partial": d["partial"],
            "reject": d["reject"],
            "total": total,
            "accept_rate": accept_rate,
        })

    # 全体統計
    total_all = sum(w["total"] for w in week_data)
    accept_all = sum(w["accept"] for w in week_data)
    partial_all = sum(w["partial"] for w in week_data)
    overall_rate = round((accept_all + partial_all * 0.5) / total_all, 3) if total_all > 0 else 0

    # トレンド判定（最新3週 vs 直前3週）
    trend = "stable"
    if len(week_data) >= 6:
        recent = sum(w["accept_rate"] for w in week_data[-3:]) / 3
        prior = sum(w["accept_rate"] for w in week_data[-6:-3]) / 3
        if recent - prior > 0.05:
            trend = "improving"
        elif prior - recent > 0.05:
            trend = "declining"
    elif len(week_data) >= 2:
        if week_data[-1]["accept_rate"] > week_data[0]["accept_rate"] + 0.05:
            trend = "improving"
        elif week_data[0]["accept_rate"] > week_data[-1]["accept_rate"] + 0.05:
            trend = "declining"

    return {
        "profile_id": profile_id,
        "total_feedback": total_all,
        "overall_accept_rate": overall_rate,
        "trend": trend,
        "weeks": week_data,
    }


def _empty_accuracy() -> dict:
    return {
        "profile_id": "",
        "total_feedback": 0,
        "overall_accept_rate": 0,
        "trend": "stable",
        "weeks": [],
    }


def _iso_week_key(iso_str: str) -> str:
    """'2026-06-05T12:34:56...' → '2026-W23' 形式に変換。"""
    try:
        import datetime
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Marketplace Reviews (Phase 6-3: 評価・レビュー)
# ---------------------------------------------------------------------------

def add_review(profile_id: str, reviewer_id: str, rating: int, review_text: str = "") -> Optional[dict]:
    """マーケットプレイスのプロファイルに星評価とレビューを追加する。"""
    if not 1 <= rating <= 5:
        raise ValueError("rating は 1〜5 の整数です")

    profile = get_public_profile(profile_id)
    if profile is None:
        raise ValueError("公開プロファイルが見つかりません")

    if profile.get("user_id") == reviewer_id:
        raise ValueError("自分のプロファイルは評価できません")

    try:
        resp = _client().table("style_profile_reviews").upsert({
            "profile_id": profile_id,
            "reviewer_id": reviewer_id,
            "rating": rating,
            "review_text": review_text[:500].strip(),
        }, on_conflict="profile_id,reviewer_id").execute()
        return resp.data[0] if resp.data else None
    except Exception as e:
        logger.warning("add_review failed: %s", e)
        return None


def get_reviews(profile_id: str, limit: int = 20) -> list[dict]:
    """プロファイルのレビュー一覧を返す（新しい順）。"""
    try:
        resp = (
            _client().table("style_profile_reviews")
            .select("id, rating, review_text, created_at, updated_at")
            .eq("profile_id", profile_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        logger.warning("get_reviews failed: %s", e)
        return []


def get_review_stats(profile_id: str) -> dict:
    """プロファイルの平均評価と星別カウントを返す。"""
    try:
        resp = (
            _client().table("style_profile_reviews")
            .select("rating")
            .eq("profile_id", profile_id)
            .execute()
        )
        rows = resp.data or []
    except Exception as e:
        logger.warning("get_review_stats failed: %s", e)
        rows = []

    if not rows:
        return {"count": 0, "average": 0.0, "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in rows:
        star = int(r.get("rating", 0))
        if star in dist:
            dist[star] += 1

    avg = round(sum(r.get("rating", 0) for r in rows) / len(rows), 2)
    return {"count": len(rows), "average": avg, "distribution": dist}
