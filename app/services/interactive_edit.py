"""
インタラクティブ編集サービス
プロンプトを解析して NLE 向け編集操作リストを生成する。
DaVinci: Python API で cut/subtitle/zoom/marker/audio を直接適用。
         speed/transition/text/color は FCPXML インポートで適用。
FCP/Premiere: 全操作を FCPXML/XMEML に変換してインポート。
"""
import json
import os
import re
from typing import Any

import anthropic
from app.services.operation_schema import OPERATION_SCHEMA as _OPERATION_SCHEMA

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _client


def parse_edit_prompt(
    prompt: str,
    transcript: dict,
    current_cuts: list,
    duration: float,
    fps: float,
    history: list,
    reference_hint: str = "",
) -> list[dict[str, Any]]:
    """
    ユーザープロンプトを Claude で解析して編集操作リストを返す。
    history = [{"role":"user"|"assistant", "content":str}, ...]
    """
    seg_lines: list[str] = []
    if isinstance(transcript, dict):
        for seg in (transcript.get("segments") or [])[:80]:
            t = f"{seg.get('start', 0):.1f}s: {seg.get('text', '').strip()}"
            seg_lines.append(t)

    transcript_preview = "\n".join(seg_lines)[:3000]

    current_cut_summary = (
        f"{len(current_cuts)} セグメント, "
        f"合計 {sum(c.get('end', 0) - c.get('start', 0) for c in current_cuts):.1f}秒"
        if current_cuts else "カット未実施"
    )

    reference_section = (
        f"\n=== 参考スタイル / 模倣対象 ===\n{reference_hint}\n"
        if reference_hint else ""
    )

    system = f"""あなたはNLE（DaVinci Resolve・Final Cut Pro・Premiere Pro）向けの動画編集AIアシスタントです。
ユーザーの編集指示を解析し、適用すべき操作のJSON配列のみを返してください。

=== 動画情報 ===
長さ: {duration:.1f}秒  FPS: {fps}
現在のカット状況: {current_cut_summary}

=== トランスクリプト（先頭80セグメント） ===
{transcript_preview}
{reference_section}
=== 操作スキーマ ===
{_OPERATION_SCHEMA}

=== ルール ===
- JSON配列のみ返す。前後の説明文は不要。
- keep_segments は 0〜{duration:.1f} 秒の範囲で指定。
- カット指示がある場合は必ず全区間をカバーする keep_segments を返す。
- 「フィラーをカット」「えー・あー・うーを除去」等は transcript を参照して具体的な区間を算出する。
- 「テンポアップ」は speed 150 + cut(無音区間を積極除去) の組み合わせが効果的。
- 「Shorts向け」は trim + cut で1分以内にまとめる。
- bgm 操作は description に具体的なアドバイスを含める（例: 「BGMトラックへ曲を追加してください」）。
- color 操作は description にプリセットの効果を説明する（例: 「warm: 暖色系の映像に仕上がります」）。
- 複数の操作を組み合わせて返してよい。
"""

    msgs: list[dict] = []
    for h in (history or [])[-8:]:
        msgs.append({"role": h["role"], "content": str(h["content"])})
    msgs.append({"role": "user", "content": prompt})

    client = _get_client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=system,
        messages=msgs,
    )

    text = resp.content[0].text.strip()

    # JSON配列を抽出
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        try:
            ops = json.loads(m.group())
            if isinstance(ops, list):
                return [o for o in ops if isinstance(o, dict) and "type" in o]
        except json.JSONDecodeError:
            pass

    return [{"type": "error", "description": f"解析失敗。raw: {text[:200]}"}]
