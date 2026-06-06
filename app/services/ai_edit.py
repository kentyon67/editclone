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
# カット精度が重要なため sonnet をデフォルトとする。CLAUDE_MODEL で環境変数上書き可
_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

_SYSTEM_PROMPT = """\
あなたはプロの動画編集者です。
ユーザーの「編集指示」と Whisper が生成したタイムスタンプ付きの書き起こしセグメントをもとに、
カットすべき区間を JSON 配列で返してください。

【出力形式】
- JSON 配列のみ。前後に説明文・マークダウン・コードブロック不要
- カットなし → []
- [{"cut_start": 0.0, "cut_end": 4.5, "reason": "冒頭挨拶"}]

【厳守ルール】
1. cut_start / cut_end はセグメントの start / end と完全に一致させる（途中カット禁止）
2. 隣接・重複するカット区間（間隔 0.1秒以内）は必ず 1 つにマージする
3. reason は 10 字以内の日本語（例: "冒頭挨拶", "言い淀み", "告知部分", "アウトロ"）
4. 「冒頭」= 最初のセグメント付近、「末尾・アウトロ」= 最後のセグメント付近 として判断
5. 発話内容の文脈を重視する。意味が繋がる区間を不要にカットしない
6. 指示に含まれていない部分は絶対にカットしない（過剰カット禁止）

【品質基準】
- 視聴者が自然に視聴できる流れを維持する
- 「えー」「あー」などのフィラーは指示がある場合のみカット
- 沈黙・間は文脈によって残すべき場合がある（全部カット不要）
"""


def analyze_transcript_for_cuts(
    segments: list[dict],
    prompt: str,
    transcript: str = "",
    total_duration: float = 0.0,
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

    duration_info = f"動画の総尺: {total_duration:.1f}秒\n\n" if total_duration > 0 else ""
    user_message = f"{duration_info}編集指示: {prompt}\n\nセグメント一覧:\n{segments_text}"

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=2048,
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
            if end > start + 0.05:
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
