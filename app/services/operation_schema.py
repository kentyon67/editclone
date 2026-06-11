"""
編集操作スキーマの共有定義。
interactive_edit.py と agent_teams.py の両方が参照する。
"""

OPERATION_SCHEMA = """
返すJSONは操作オブジェクトの配列です。複数同時指定可。
各操作には必ず "description" フィールドで日本語の説明を含める。

━━ 操作タイプ一覧 ━━

1. カット構成変更（最重要）
{"type":"cut", "keep_segments":[{"start":float,"end":float},...], "description":"説明"}
- keep_segments は保持する区間。カットしたい部分は除外する。
- 指定した区間が連結されてタイムラインになる。

2. 冒頭/末尾トリム
{"type":"trim", "start_seconds":float, "end_seconds":float, "description":"説明"}
- start_seconds: 冒頭から何秒カットするか（0以上）
- end_seconds: 末尾から何秒カットするか（0以上）

3. 再生速度変更
{"type":"speed", "speed_percent":int, "description":"説明"}
- 100=等速, 150=1.5倍速, 200=2倍速, 50=0.5倍速
- DaVinci: FCPXML インポートで適用。FCP/Premiere: 直接適用。

4. 字幕追加
{"type":"subtitle", "description":"説明"}
- SRT ファイルを自動生成してタイムラインに追加する。

5. ズーム
{"type":"zoom", "zoom_level":float, "description":"説明"}
- 1.0=等倍, 1.05=subtle(5%拡大), 1.10=punch(10%拡大)
- DaVinci: ZoomX/ZoomY で即時適用。FCP/Premiere: FCPXML で適用。

6. トランジション追加（クリップ間）
{"type":"transition", "style":"dissolve|fade_to_black|wipe", "duration":float, "description":"説明"}
- duration: トランジション時間（秒）、デフォルト 0.5s
- DaVinci: FCPXML インポートで適用。

7. テキストオーバーレイ
{"type":"text", "text":"表示テキスト", "start":float, "duration":float, "description":"説明"}
- start: 表示開始秒, duration: 表示時間（秒）
- DaVinci: FCPXML インポートで適用。

8. 音量・フェード調整
{"type":"audio", "target":"all|voice|bgm", "volume_db":float, "description":"説明"}
- volume_db: +3.0=+3dB, -6.0=-6dB など
- DaVinci: 直接適用可能（SetProperty）。

9. カラー補正
{"type":"color", "preset":"warm|cool|cinematic|bright|dark|bw", "description":"説明"}
- DaVinci: カラーページに自動遷移。FCP/Premiere: FCPXML の colorCorrection で適用。

10. マーカー追加
{"type":"marker", "moments":[{"time":float,"label":"str","color":"red|orange|yellow|green|blue|purple"},...], "description":"説明"}
- time: 秒単位のタイムコード

11. BGM追加（案内のみ）
{"type":"bgm", "mood":"upbeat|calm|dramatic|happy|sad|none", "description":"説明"}
- NLE の BGM 追加 API は存在しないため、案内メッセージを返す。
"""

# DaVinci Python API 非対応（FCPXML インポートが必要）の操作タイプ
FCPXML_REQUIRED_TYPES = frozenset({"speed", "transition", "text", "color"})
