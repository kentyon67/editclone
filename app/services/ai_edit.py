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
You are a professional video editor. Based on the user's editing instructions and \
Whisper-generated timestamped transcript segments, return a JSON array of segments to cut.
Instructions may be in Japanese or English — respond in the same language as the instruction.

[OUTPUT FORMAT]
- JSON array only. No explanation, markdown, or code blocks.
- No cuts → []
- Example: [{"cut_start": 0.0, "cut_end": 4.5, "reason": "opening greeting"}]

[STRICT RULES]
1. cut_start / cut_end must exactly match a segment's start / end value (no mid-segment cuts)
2. Adjacent or overlapping cut ranges (gap ≤ 0.1s) must be merged into one
3. "reason" must be ≤ 10 characters (concise label, e.g. "opening", "filler", "promo", "outro")
4. "opening" = segments near the start; "outro/closing" = segments near the end
5. Preserve content flow — do not cut segments that connect meaning to what follows
6. Never cut content not covered by the instruction (no over-cutting)

[FILLER WORDS — cut only when instructed]
- Japanese: えー、あー、えーと、まあ、そのー、なんか、あのー、うーん
- English: um, uh, like, you know, basically, literally, I mean, so um, kind of

[COMMON EDIT PATTERNS]
- "opening cut" / "冒頭カット" — remove greeting/intro before main content begins
- "outro cut" / "アウトロカット" — remove post-content ad-libs and channel promotion
- "filler cut" / "言い淀み除去" — remove filler words and repeated phrases
- "promo cut" / "告知カット" — remove subscribe/like-button callouts and sponsor segments
- "silence only" / "無音のみ" — return [] (use silence detection only, no AI cuts)

[QUALITY STANDARDS]
- Maintain natural viewing flow; do not create jarring jumps
- Pauses can be meaningful — do not cut all silence
- Do not split a coherent sentence or thought across a cut boundary
"""


def analyze_transcript_for_cuts(
    segments: list[dict],
    prompt: str,
    transcript: str = "",
    total_duration: float = 0.0,
    style_context: dict | None = None,
) -> list[dict]:
    """
    Claude API でトランスクリプトを分析し、ユーザー指示に基づくカット候補を返す。
    segments: [{"start": float, "end": float, "text": str}, ...]
    prompt: ユーザーの編集指示（例: "冒頭の挨拶をカット"）
    style_context: アクティブなStyle Profileの文脈 {"name", "description", "default_prompt", ...}
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

    # Style Profile コンテキストをプロンプトに組み込む
    style_section = ""
    if style_context:
        parts = []
        if style_context.get("name"):
            parts.append(f"スタイル名: {style_context['name']}")
        if style_context.get("description"):
            parts.append(f"スタイル説明: {style_context['description']}")
        if style_context.get("default_prompt"):
            parts.append(f"ベースプロンプト: {style_context['default_prompt']}")
        if style_context.get("noise_db"):
            parts.append(f"無音閾値: {style_context['noise_db']}dB")
        if parts:
            style_section = "\n\n[USER STYLE PROFILE — prioritize these preferences]\n" + "\n".join(parts)

    system_with_style = _SYSTEM_PROMPT + style_section

    duration_info = f"動画の総尺: {total_duration:.1f}秒\n\n" if total_duration > 0 else ""
    user_message = f"{duration_info}編集指示: {prompt}\n\nセグメント一覧:\n{segments_text}"

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=_MODEL,
            max_tokens=2048,
            system=system_with_style,
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
