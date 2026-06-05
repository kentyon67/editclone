"""
Claude API を使ったインテリジェントな編集提案。
ANTHROPIC_API_KEY が未設定の場合は空リストを返してサイレントに降格する。
"""
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_SYSTEM_PROMPT = """\
あなたはプロの動画編集アシスタントです。
ユーザーが与えた「編集指示」と、Whisper で生成したタイムスタンプ付きの書き起こしセグメントを元に、
動画からカットすべき区間を特定してください。

回答は JSON 配列のみ（他のテキストを含めない）で返してください。
形式: [{"cut_start": 0.0, "cut_end": 4.5, "reason": "理由"}]
カットが不要な場合は空配列 [] を返してください。

ルール:
- タイムスタンプは元動画の秒数（float）で指定する
- 隣接するカットはまとめてよい
- reason は日本語で簡潔に（〜10字）
- 発話の途中でカットしない（セグメント境界を尊重する）
"""


def analyze_transcript_for_cuts(
    segments: list[dict],
    prompt: str,
    transcript: str = "",
) -> list[dict]:
    """
    Claude API でトランスクリプトを分析し、ユーザー指示に基づくカット候補を返す。
    segments: [{"start": float, "end": float, "text": str}, ...]
    prompt: ユーザーの編集指示（例: "冒頭の挨拶をカット"）
    返値: [{"cut_start": float, "cut_end": float, "reason": str, "source": "ai"}, ...]
    """
    if not ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY が未設定のため AI カットをスキップします")
        return []

    if not prompt or not segments:
        return []

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic パッケージが未インストールです: pip install anthropic")
        return []

    segments_text = "\n".join(
        f"[{s['start']:.2f}s - {s['end']:.2f}s] {s['text']}" for s in segments
    )
    user_message = f"編集指示: {prompt}\n\nセグメント一覧:\n{segments_text}"

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text.strip()

        # JSON 配列を抽出（Claude が前後に説明文を付けることがある）
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return []

        cuts = json.loads(m.group())
        result = []
        for c in cuts:
            start = float(c.get("cut_start", 0))
            end = float(c.get("cut_end", 0))
            if end > start:
                result.append({
                    "cut_start": round(start, 3),
                    "cut_end": round(end, 3),
                    "duration": round(end - start, 3),
                    "reason": c.get("reason", "AI提案"),
                    "source": "ai",
                })
        logger.info("Claude API から %d 件のカット提案を取得", len(result))
        return result

    except Exception as e:
        logger.warning("Claude API エラー（AI カットをスキップ）: %s", e)
        return []


def merge_cuts(silence_cuts: list[dict], ai_cuts: list[dict]) -> list[dict]:
    """
    無音カットと AI カットをマージし、重複・隣接を統合して返す。
    """
    all_cuts = silence_cuts + ai_cuts
    if not all_cuts:
        return []

    sorted_cuts = sorted(all_cuts, key=lambda c: c["cut_start"])
    merged: list[dict] = []
    current = dict(sorted_cuts[0])

    for cut in sorted_cuts[1:]:
        if cut["cut_start"] <= current["cut_end"] + 0.05:
            current["cut_end"] = max(current["cut_end"], cut["cut_end"])
            current["duration"] = round(current["cut_end"] - current["cut_start"], 3)
            if cut.get("source") == "ai" and current.get("source") != "ai":
                current["reason"] = cut["reason"]
                current["source"] = "ai+silence"
        else:
            merged.append(current)
            current = dict(cut)

    merged.append(current)
    return merged
