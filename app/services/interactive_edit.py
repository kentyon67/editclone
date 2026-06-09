"""
インタラクティブ編集サービス
プロンプトを解析して DaVinci Resolve 向け編集操作リストを生成する。
"""
import json
import os
import re
from typing import Any

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    return _client


_OPERATION_SCHEMA = """
返すJSONは操作オブジェクトの配列です。複数同時指定可。

操作タイプ一覧:

1. カット構成変更
{"type":"cut", "keep_segments":[{"start":float,"end":float},...], "description":"説明"}

2. 再生速度
{"type":"speed", "speed_percent":int, "description":"説明"}
※ 100=通常 150=1.5倍 200=2倍

3. 音量調整
{"type":"volume", "target":"all|voice|bgm", "volume_db":float, "description":"説明"}

4. 字幕追加
{"type":"subtitle", "description":"説明"}

5. ズーム
{"type":"zoom", "zoom_level":float, "description":"説明"}
※ 1.0=等倍 1.1=10%拡大

6. 冒頭/末尾トリム
{"type":"trim", "start_seconds":float, "end_seconds":float, "description":"説明"}

7. カラー調整(参考指示)
{"type":"color", "preset":"warm|cool|cinematic|bright|dark|bw", "description":"説明"}

8. BGM追加(参考指示)
{"type":"bgm", "mood":"upbeat|calm|dramatic|happy|none", "description":"説明"}

9. マーカー追加
{"type":"marker", "moments":[{"time":float,"label":"str"}], "description":"説明"}
"""


def parse_edit_prompt(
    prompt: str,
    transcript: dict,
    current_cuts: list,
    duration: float,
    fps: float,
    history: list,
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
        f"合計 {sum(c.get('end',0)-c.get('start',0) for c in current_cuts):.1f}秒"
        if current_cuts else "カット未実施"
    )

    system = f"""あなたはDaVinci Resolve向けの動画編集AIアシスタントです。
ユーザーの編集指示を解析し、適用すべき操作のJSON配列のみを返してください。

=== 動画情報 ===
長さ: {duration:.1f}秒  FPS: {fps}
現在のカット状況: {current_cut_summary}

=== トランスクリプト ===
{transcript_preview}

=== 操作スキーマ ===
{_OPERATION_SCHEMA}

=== ルール ===
- JSON配列のみ返す。前後の説明文は不要
- keep_segments は 0〜{duration:.1f} 秒の範囲で指定
- カット指示がある場合は必ず全区間をカバーする keep_segments を返す
- 「フィラーをカット」「無音を削除」等は transcript を参照して具体的な区間を算出する
- 複数の操作を同時に組み合わせてよい
"""

    msgs: list[dict] = []
    for h in (history or [])[-8:]:
        msgs.append({"role": h["role"], "content": str(h["content"])})
    msgs.append({"role": "user", "content": prompt})

    client = _get_client()
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
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

    # フォールバック
    return [{"type": "error", "description": f"解析失敗。raw: {text[:200]}"}]
