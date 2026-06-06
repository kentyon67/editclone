"""
B-roll 提案サービス — トランスクリプトを分析してB-rollが効果的な箇所を提案する。
Claude API を使ってコンテキストを理解し、視覚補強が必要な瞬間を特定する。
"""
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_SYSTEM_PROMPT = """\
You are a professional video editor specializing in B-roll placement. \
Analyze the transcript segments and identify timestamps where inserting B-roll \
footage would enhance viewer engagement, clarify concepts, or improve visual storytelling.

[OUTPUT FORMAT]
- JSON array only. No explanation, markdown, or code blocks.
- No suggestions → []
- Example:
[
  {
    "start": 12.5,
    "end": 18.0,
    "keyword": "スマートフォン操作",
    "description": "スマホアプリを説明しているため、操作画面のB-rollが効果的",
    "b_roll_type": "screen_capture",
    "priority": "high"
  }
]

[B-ROLL TYPES]
- "product_demo": 製品・サービスの実演映像
- "screen_capture": PC/スマホ画面の操作映像
- "concept_visual": 抽象概念を視覚化する映像（例: お金→札束、AI→回路）
- "location_shot": 言及された場所・施設の映像
- "talking_head": インタビューや話者のクローズアップ
- "data_visualization": グラフ・図表・統計の表示
- "action_shot": 説明している行動や動作の映像

[PRIORITY LEVELS]
- "high": ここのB-rollがないと視聴者が離脱しやすい（純音声や長い説明が続く箇所）
- "medium": B-rollがあるとテンポ改善になる箇所
- "low": あれば良いが必須ではない箇所

[RULES]
1. start/end は必ずセグメントの start/end と一致させること
2. 1件あたり最低3秒以上の区間を対象とすること
3. 音声が重要な箇所（感情的・結論的な発言）はB-rollを提案しないこと
4. 最大15件まで。多すぎる提案は避ける
5. keyword は日本語または英語で10文字以内の検索ワード
"""


def suggest_broll(
    segments: list[dict],
    prompt: str = "",
    total_duration: float = 0.0,
) -> list[dict]:
    """
    トランスクリプトセグメントからB-roll提案を生成する。
    segments: [{"start": float, "end": float, "text": str}, ...]
    返値: [{"start", "end", "keyword", "description", "b_roll_type", "priority"}, ...]
    """
    if not ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY 未設定のためB-roll提案をスキップ")
        return []

    if not segments:
        return []

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic パッケージが未インストールです")
        return []

    segments_text = "\n".join(
        f"[{s['start']:.2f}s - {s['end']:.2f}s] {s['text']}" for s in segments
    )

    context = ""
    if prompt:
        context = f"動画の編集方針: {prompt}\n\n"
    if total_duration > 0:
        context += f"総尺: {total_duration:.1f}秒\n\n"

    user_message = (
        f"{context}以下のトランスクリプトを分析し、"
        "B-rollを挿入すると効果的な箇所を提案してください。\n\n"
        f"セグメント一覧:\n{segments_text}"
    )

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text.strip()

        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return []

        suggestions = json.loads(m.group())
        result = []
        for s in suggestions:
            start = float(s.get("start", 0))
            end = float(s.get("end", 0))
            if end - start < 2.5:
                continue
            result.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(end - start, 3),
                "keyword": str(s.get("keyword", ""))[:40],
                "description": str(s.get("description", ""))[:200],
                "b_roll_type": s.get("b_roll_type", "concept_visual"),
                "priority": s.get("priority", "medium"),
            })

        result.sort(key=lambda x: (
            {"high": 0, "medium": 1, "low": 2}.get(x["priority"], 1),
            x["start"],
        ))
        logger.info("B-roll提案: %d 件", len(result))
        return result[:15]

    except Exception as e:
        logger.warning("B-roll提案エラー: %s", e)
        return []
