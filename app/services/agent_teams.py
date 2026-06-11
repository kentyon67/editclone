"""
Agent Teams — 複数の専門 AI エージェントを並列実行して編集操作を生成するオーケストレーター。

アーキテクチャ:
  1. 4 つの専門エージェントを ThreadPoolExecutor で同時実行する（各タイムアウト 30s）
  2. 各エージェントは _OPERATION_SCHEMA 準拠の操作リストを返す
  3. マージルール:
     - cut  : 全エージェントの keep_segments を union（最も保守的な保持）
     - speed: 複数提案は平均値を使用
     - その他: 後勝ち（最後のエージェントが上書き）
  4. claude-haiku-4-5-20251001 を個別エージェントに使用（高速・低コスト）
  5. claude-sonnet-4-6 でエージェントレポートを合成して最終説明を生成
"""

from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_AGENT_TIMEOUT_SECONDS = 30
_MAX_WORKERS = 4

# ── モデル定義 ──────────────────────────────────────────────────────────────
_AGENT_MODEL = "claude-haiku-4-5-20251001"
_SYNTHESIS_MODEL = "claude-sonnet-4-6"

# ── 専門エージェントの役割定義 ─────────────────────────────────────────────
AGENT_ROLES: dict[str, str] = {
    "cut_agent":   "専門家: 不要シーン・無音・フィラーの除去",
    "style_agent": "専門家: テロップスタイル・カラー・トランジション",
    "pacing_agent": "専門家: テンポ・速度・BGM提案",
    "hook_agent":  "専門家: 冒頭フック・エンディング・バイラル要素",
}

# ── 操作スキーマ（interactive_edit.py と同一定義） ─────────────────────────
_OPERATION_SCHEMA = """
返すJSONは操作オブジェクトの配列です。複数同時指定可。
各操作には必ず "description" フィールドで日本語の説明を含める。

━━ 操作タイプ一覧 ━━

1. カット構成変更（最重要）
{"type":"cut", "keep_segments":[{"start":float,"end":float},...], "description":"説明"}
- keep_segments は保持する区間。カットしたい部分は除外する。

2. 冒頭/末尾トリム
{"type":"trim", "start_seconds":float, "end_seconds":float, "description":"説明"}

3. 再生速度変更
{"type":"speed", "speed_percent":int, "description":"説明"}
- 100=等速, 150=1.5倍速, 200=2倍速, 50=0.5倍速

4. 字幕追加
{"type":"subtitle", "description":"説明"}

5. ズーム
{"type":"zoom", "zoom_level":float, "description":"説明"}
- 1.0=等倍, 1.05=subtle, 1.10=punch

6. トランジション追加
{"type":"transition", "style":"dissolve|fade_to_black|wipe", "duration":float, "description":"説明"}

7. テキストオーバーレイ
{"type":"text", "text":"表示テキスト", "start":float, "duration":float, "description":"説明"}

8. 音量・フェード調整
{"type":"audio", "target":"all|voice|bgm", "volume_db":float, "description":"説明"}

9. カラー補正
{"type":"color", "preset":"warm|cool|cinematic|bright|dark|bw", "description":"説明"}

10. マーカー追加
{"type":"marker", "moments":[{"time":float,"label":"str","color":"red|orange|yellow|green|blue|purple"},...], "description":"説明"}

11. BGM追加（案内のみ）
{"type":"bgm", "mood":"upbeat|calm|dramatic|happy|sad|none", "description":"説明"}
"""

# ── エージェント固有のシステムプロンプト ────────────────────────────────────
_AGENT_SYSTEM_PROMPTS: dict[str, str] = {
    "cut_agent": """\
あなたは動画カット専門のAI編集エージェントです。
役割: 不要シーン・無音・フィラーワード（えー、あの、まあ等）の除去に集中してください。

指示:
- トランスクリプトを詳細に分析し、カット提案を keep_segments で返してください
- フィラーワード、長い無音区間、繰り返し表現を積極的にカットする
- "cut" 操作を必ず含める（カット不要の場合も理由を述べた上で全区間を返す）
- 他の種類の操作（speed, color 等）は返さない

{schema}

JSON 配列のみ返す。前後の説明文は不要。
""",

    "style_agent": """\
あなたは動画スタイル専門のAI編集エージェントです。
役割: テロップ（字幕）スタイル・カラーグレーディング・トランジション効果の提案に集中してください。

指示:
- ユーザーのプロンプトと動画内容から最適なビジュアルスタイルを提案する
- "subtitle", "color", "transition", "text", "zoom" 操作を適宜組み合わせる
- TikTok/Shorts 向けなら字幕必須、明るい色調を推奨
- "cut" 操作は返さない

{schema}

JSON 配列のみ返す。前後の説明文は不要。
""",

    "pacing_agent": """\
あなたは動画テンポ専門のAI編集エージェントです。
役割: 映像のテンポ・速度・リズム感の最適化とBGM提案に集中してください。

指示:
- 再生速度変更（"speed"）でテンポを調整する
- BGM ムード（"bgm"）を提案する
- 音量バランス（"audio"）を調整する
- ユーザーの目的（バイラル、教育、Vlog等）に合わせたペースを提案
- "cut" 操作は返さない

{schema}

JSON 配列のみ返す。前後の説明文は不要。
""",

    "hook_agent": """\
あなたは動画エンゲージメント専門のAI編集エージェントです。
役割: 冒頭フック・エンディング構成・バイラル要素の強化に集中してください。

指示:
- 冒頭3秒以内に視聴者を引き込む構成（"trim" で冒頭の挨拶をカット等）
- 重要ポイントにマーカー（"marker"）を追加する
- テキストオーバーレイ（"text"）でタイトルや強調文字を提案
- TikTok/Shorts のバイラル要素（テンポの速さ、字幕、フック）を強調
- "cut" 操作は単純な冒頭トリムのみ許可

{schema}

JSON 配列のみ返す。前後の説明文は不要。
""",
}


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _build_context(
    transcript: dict,
    cuts: list,
    duration: float,
    fps: float,
    user_prompt: str,
    reference_hint: str = "",
) -> str:
    """全エージェントに共通の動画コンテキストを生成する。"""
    seg_lines: list[str] = []
    if isinstance(transcript, dict):
        for seg in (transcript.get("segments") or [])[:60]:
            t = f"{seg.get('start', 0):.1f}s: {seg.get('text', '').strip()}"
            seg_lines.append(t)

    transcript_preview = "\n".join(seg_lines)[:2500]
    cut_summary = (
        f"{len(cuts)} セグメント, 合計 {sum(c.get('end', 0) - c.get('start', 0) for c in cuts):.1f}秒"
        if cuts else "カット未実施"
    )

    reference_section = (
        f"\n=== 参考スタイル / 模倣対象 ===\n{reference_hint}"
        if reference_hint else ""
    )

    return (
        f"=== ユーザー指示 ===\n{user_prompt}\n\n"
        f"=== 動画情報 ===\n"
        f"長さ: {duration:.1f}秒  FPS: {fps}\n"
        f"現在のカット状況: {cut_summary}\n\n"
        f"=== トランスクリプト（先頭60セグメント） ===\n{transcript_preview}"
        f"{reference_section}"
    )


def _run_single_agent(
    agent_name: str,
    role_desc: str,
    context: str,
    duration: float,
) -> tuple[str, list[dict], str]:
    """
    1 つのエージェントを実行して操作リストを返す。

    Returns:
        (agent_name, operations, report_text)
    """
    system_template = _AGENT_SYSTEM_PROMPTS.get(agent_name, "")
    system = system_template.format(schema=_OPERATION_SCHEMA)

    user_message = (
        f"{context}\n\n"
        f"あなたの役割: {role_desc}\n"
        f"上記の動画に対して、あなたの専門領域の操作のみを提案してください。\n"
        f"keep_segments の時間は 0〜{duration:.1f} 秒の範囲で指定してください。"
    )

    client = _get_client()
    resp = client.messages.create(
        model=_AGENT_MODEL,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )

    text = resp.content[0].text.strip()

    # JSON 配列を抽出
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            ops = json.loads(m.group())
            if isinstance(ops, list):
                valid_ops = [o for o in ops if isinstance(o, dict) and "type" in o]
                return agent_name, valid_ops, text
        except json.JSONDecodeError:
            pass

    logger.warning("[%s] JSON 解析失敗: %s", agent_name, text[:200])
    return agent_name, [], text


def _union_keep_segments(all_segments_lists: list[list[dict]], duration: float) -> list[dict]:
    """
    複数の keep_segments リストを union（和集合）する。
    全エージェントが「保持する」と合意した区間のみを保持する（最も保守的）。

    実装: 各エージェントの keep_segments を「保持フラグ」配列に変換し、
    全エージェントが True の区間だけを残す。解像度 = 0.1s。
    """
    if not all_segments_lists:
        return [{"start": 0.0, "end": round(duration, 3)}] if duration > 0 else []

    # 有効なリストのみ使用
    valid_lists = [lst for lst in all_segments_lists if lst]
    if not valid_lists:
        return [{"start": 0.0, "end": round(duration, 3)}] if duration > 0 else []

    resolution = 0.1  # 秒単位の解像度
    num_frames = max(1, int(duration / resolution) + 1)

    # 各エージェントの保持区間を bool 配列に変換
    agent_keep_arrays: list[list[bool]] = []
    for segs in valid_lists:
        keep = [False] * num_frames
        for seg in segs:
            s_idx = max(0, int(float(seg.get("start", 0)) / resolution))
            e_idx = min(num_frames - 1, int(float(seg.get("end", 0)) / resolution))
            for i in range(s_idx, e_idx + 1):
                keep[i] = True
        agent_keep_arrays.append(keep)

    # 全エージェントが保持 → 保持（AND）
    union_keep = [all(arr[i] for arr in agent_keep_arrays) for i in range(num_frames)]

    # bool 配列から keep_segments を再構築
    result: list[dict] = []
    in_segment = False
    seg_start = 0.0

    for i, keep in enumerate(union_keep):
        t = i * resolution
        if keep and not in_segment:
            seg_start = t
            in_segment = True
        elif not keep and in_segment:
            seg_end = t
            if seg_end - seg_start >= 0.1:
                result.append({"start": round(seg_start, 3), "end": round(seg_end, 3)})
            in_segment = False

    if in_segment:
        seg_end = min(duration, num_frames * resolution)
        if seg_end - seg_start >= 0.1:
            result.append({"start": round(seg_start, 3), "end": round(seg_end, 3)})

    # フォールバック: 全区間が除去された場合は元の最大範囲を返す
    if not result and duration > 0:
        return [{"start": 0.0, "end": round(duration, 3)}]

    return result


def _merge_operations(
    agent_results: dict[str, list[dict]],
    duration: float,
) -> list[dict]:
    """
    複数エージェントの操作リストをマージする。

    マージルール:
      - cut    : keep_segments の union（最も保守的な保持）
      - speed  : 複数提案の平均値
      - その他 : 後勝ち（エージェント順: cut → pacing → style → hook）
    """
    # エージェントの処理順序（カット系を最初に）
    agent_order = ["cut_agent", "pacing_agent", "style_agent", "hook_agent"]

    merged: dict[str, dict[str, Any]] = {}  # type -> operation

    # cut 操作の keep_segments を収集
    cut_keep_segments_list: list[list[dict]] = []

    for agent_name in agent_order:
        ops = agent_results.get(agent_name) or []
        for op in ops:
            op_type = op.get("type", "")
            if not op_type:
                continue

            if op_type == "cut":
                segs = op.get("keep_segments") or []
                if segs:
                    cut_keep_segments_list.append(segs)

            elif op_type == "speed":
                if "speed" not in merged:
                    merged["speed"] = dict(op)
                else:
                    # 平均を計算
                    prev_pct = float(merged["speed"].get("speed_percent", 100))
                    new_pct = float(op.get("speed_percent", 100))
                    avg_pct = round((prev_pct + new_pct) / 2)
                    merged["speed"] = {
                        "type": "speed",
                        "speed_percent": avg_pct,
                        "description": f"速度 {avg_pct}%（複数エージェント平均）",
                    }

            else:
                # 後勝ち（同じタイプを上書き）
                merged[op_type] = dict(op)

    # cut 操作を union してマージ済み dict に追加
    if cut_keep_segments_list:
        union_segs = _union_keep_segments(cut_keep_segments_list, duration)
        merged["cut"] = {
            "type": "cut",
            "keep_segments": union_segs,
            "description": f"エージェント協調カット: {len(union_segs)} セグメント保持",
        }

    # cut を先頭にして返す
    result: list[dict] = []
    if "cut" in merged:
        result.append(merged.pop("cut"))
    result.extend(merged.values())

    return result


def _synthesize_reports(
    agent_reports: dict[str, str],
    operations: list[dict],
    user_prompt: str,
    context: str,
) -> str:
    """
    claude-sonnet-4-6 で各エージェントのレポートを合成して最終説明を生成する。
    """
    reports_text = "\n\n".join(
        f"【{name}】\n{report[:500]}"
        for name, report in agent_reports.items()
        if report
    )

    op_summary = ", ".join(op.get("type", "?") for op in operations) or "なし"

    system = (
        "あなたは動画編集AIアシスタントです。複数の専門エージェントの分析結果を"
        "統合して、ユーザーへの分かりやすい最終説明を日本語で提供してください。"
        "100〜200字程度で簡潔にまとめてください。"
    )

    user_message = (
        f"ユーザー指示: {user_prompt}\n\n"
        f"適用される操作: {op_summary}\n\n"
        f"各エージェントの分析:\n{reports_text}\n\n"
        "上記を統合した最終説明を提供してください。"
    )

    try:
        client = _get_client()
        resp = client.messages.create(
            model=_SYNTHESIS_MODEL,
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.warning("synthesis エラー: %s", e)
        op_types = [op.get("type", "?") for op in operations]
        return f"{len(operations)} 件の操作を適用します: {', '.join(op_types)}"


def run_agent_team(
    transcript: dict,
    cuts: list,
    duration: float,
    fps: float,
    user_prompt: str,
    history: list | None = None,
    reference_hint: str = "",
) -> dict:
    """
    複数の専門エージェントを並列実行して編集操作リストを生成する。

    Args:
        transcript: Whisper トランスクリプト（{"segments": [...]} 形式）
        cuts: 現在のカット状況（keep_segments 形式）
        duration: 動画の長さ（秒）
        fps: フレームレート
        user_prompt: ユーザーの編集指示
        history: 会話履歴（現時点では未使用、将来の拡張用）

    Returns:
        {
            "operations": [...],       # マージ・重複除去済みの操作リスト
            "agent_reports": {         # 各エージェントの推論テキスト
                "cut_agent": "...",
                "style_agent": "...",
                "pacing_agent": "...",
                "hook_agent": "...",
            },
            "synthesis": "...",        # 最終統合説明
            "agents_succeeded": [...], # 成功したエージェント名リスト
            "agents_failed": [...],    # タイムアウト/失敗エージェント名リスト
        }
    """
    context = _build_context(transcript, cuts, duration, fps, user_prompt, reference_hint)

    agent_reports: dict[str, str] = {}
    agent_operations: dict[str, list[dict]] = {}
    agents_succeeded: list[str] = []
    agents_failed: list[str] = []

    # ── 並列実行 ──────────────────────────────────────────────────────────
    futures = {}
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        for agent_name, role_desc in AGENT_ROLES.items():
            future = executor.submit(
                _run_single_agent,
                agent_name,
                role_desc,
                context,
                duration,
            )
            futures[future] = agent_name

        for future in as_completed(futures, timeout=_AGENT_TIMEOUT_SECONDS + 5):
            agent_name = futures[future]
            try:
                returned_name, ops, report = future.result(timeout=_AGENT_TIMEOUT_SECONDS)
                agent_operations[returned_name] = ops
                agent_reports[returned_name] = report
                agents_succeeded.append(returned_name)
                logger.info("[%s] 完了: %d 操作", returned_name, len(ops))
            except FuturesTimeoutError:
                agents_failed.append(agent_name)
                agent_reports[agent_name] = "(タイムアウト)"
                logger.warning("[%s] タイムアウト（%d秒）", agent_name, _AGENT_TIMEOUT_SECONDS)
            except Exception as e:
                agents_failed.append(agent_name)
                agent_reports[agent_name] = f"(エラー: {e})"
                logger.warning("[%s] エラー: %s", agent_name, e)

    # ── マージ ────────────────────────────────────────────────────────────
    merged_operations = _merge_operations(agent_operations, duration)

    # ── 合成 ──────────────────────────────────────────────────────────────
    synthesis = _synthesize_reports(
        agent_reports=agent_reports,
        operations=merged_operations,
        user_prompt=user_prompt,
        context=context,
    )

    logger.info(
        "Agent team 完了: %d エージェント成功, %d 失敗, %d 操作生成",
        len(agents_succeeded),
        len(agents_failed),
        len(merged_operations),
    )

    return {
        "operations": merged_operations,
        "agent_reports": agent_reports,
        "synthesis": synthesis,
        "agents_succeeded": agents_succeeded,
        "agents_failed": agents_failed,
    }


def should_use_teams(prompt: str) -> bool:
    """
    プロンプトの複雑さに基づいてエージェントチームを使うべきか判定する。

    条件:
      - プロンプト長 > 20 文字
      - カンマ（複数指示の区切り）を含む
      - 複雑キーワードを含む（バイラル、TikTok、Shorts 等）
    """
    if len(prompt) > 20:
        return True
    if "," in prompt or "、" in prompt:
        return True
    complex_keywords = [
        "viral", "バイラル", "tiktok", "ティックトック", "shorts", "ショーツ",
        "プロ", "professional", "完璧", "最高", "全部", "すべて",
    ]
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in complex_keywords)
