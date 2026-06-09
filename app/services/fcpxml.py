import uuid
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

from app.services.cut_suggestion import suggest_cuts
from app.services.video_info import extract_video_info


def _frame_duration(fps: float) -> str:
    """FPS から FCPXML frameDuration 有理数文字列を返す（NTSC 対応）。"""
    if abs(fps - 23.976) < 0.05:
        return "1001/24000s"
    if abs(fps - 29.97) < 0.05:
        return "1001/30000s"
    if abs(fps - 47.952) < 0.05:
        return "1001/48000s"
    if abs(fps - 59.94) < 0.05:
        return "1001/60000s"
    fps_int = int(round(fps))
    return f"1/{fps_int}s"


def _format_name(fps: float, height: int) -> str:
    """FCP フォーマット名を返す（NTSC は 4 桁 fps 表記）。"""
    if abs(fps - 23.976) < 0.05:
        return f"FFVideoFormat{height}p2398"
    if abs(fps - 29.97) < 0.05:
        return f"FFVideoFormat{height}p2997"
    if abs(fps - 47.952) < 0.05:
        return f"FFVideoFormat{height}p4795"
    if abs(fps - 59.94) < 0.05:
        return f"FFVideoFormat{height}p5994"
    fps_int = int(round(fps))
    return f"FFVideoFormat{height}p{fps_int}"


def _t(seconds: float) -> str:
    """Float 秒 → FCPXML 有理数時刻文字列 (ms 精度)"""
    ms = round(seconds * 1000)
    return f"{ms}/1000s"


def _hex_to_fcpxml_color(hex_color: str) -> str:
    """#RRGGBB → 'R G B 1' (FCPXML normalized RGBA, 0.0–1.0)"""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return f"{r:.4f} {g:.4f} {b:.4f} 1"
    return "1 1 1 1"


def _kept_segments(
    silence: list[dict], total: float
) -> list[tuple[float, float]]:
    """無音区間を除いた残存区間のリストを返す"""
    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for seg in sorted(silence, key=lambda s: s["cut_start"]):
        start, end = seg["cut_start"], seg["cut_end"]
        if start > cursor:
            segments.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < total:
        segments.append((cursor, total))
    return segments


# ---------------------------------------------------------------------------
# Operation helpers
# ---------------------------------------------------------------------------

def _speed_factor(operations: list[dict]) -> float:
    """操作リストから速度倍率を返す (1.0 = 等速)。"""
    for op in (operations or []):
        if op.get("type") == "speed":
            pct = float(op.get("speed_percent", 100))
            return max(0.1, pct / 100.0)
    return 1.0


def _audio_db(operations: list[dict]) -> float | None:
    """操作リストから音量調整 dB を返す。"""
    for op in (operations or []):
        if op.get("type") == "audio":
            db = op.get("volume_db")
            if db is not None:
                return float(db)
    return None


def _transition_dur(operations: list[dict]) -> float:
    """トランジション操作があれば持続時間(秒)を返す。なければ 0。"""
    for op in (operations or []):
        if op.get("type") == "transition":
            return max(0.1, float(op.get("duration", 0.5)))
    return 0.0


def _text_ops(operations: list[dict]) -> list[dict]:
    return [op for op in (operations or []) if op.get("type") == "text"]


def _color_preset(operations: list[dict]) -> str | None:
    for op in (operations or []):
        if op.get("type") == "color":
            return str(op.get("preset", ""))
    return None


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_fcpxml(
    video_path: Path,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
    cuts: list[dict] | None = None,
    video_info: dict | None = None,
    segments: list[dict] | None = None,
    caption_style: dict | None = None,
    operations: list[dict] | None = None,
) -> str:
    """FCPXML を生成する。

    segments はカット後タイムラインに再マッピング済みの字幕セグメント。
    operations に Claude が生成した操作リストを渡すとリッチ出力になる:
      speed, audio, transition, text, color
    """
    if video_info is None:
        video_info = extract_video_info(video_path)

    total_sec = float(video_info.get("duration_seconds") or 0.0)
    width = int(video_info.get("width") or 1920)
    height = int(video_info.get("height") or 1080)
    fps = float(video_info.get("fps") or 30.0)

    if cuts is None:
        cuts = suggest_cuts(video_path, noise_db=noise_db, min_duration=min_duration)
    kept = _kept_segments(cuts, total_sec)

    speed = _speed_factor(operations)
    audio_db_val = _audio_db(operations)
    tran_dur = _transition_dur(operations)
    texts = _text_ops(operations)
    color = _color_preset(operations)

    # 速度・トランジションを加味したタイムライン総尺
    n_transitions = max(0, len(kept) - 1) if tran_dur > 0 else 0
    timeline_dur = sum((e - s) / speed for s, e in kept) + n_transitions * tran_dur

    asset_uid = uuid.uuid4().hex.upper()
    fmt_id = "r1"
    asset_id = "r2"
    ts_id = "ts1"
    ts_title_id = "ts2"

    root = ET.Element("fcpxml", version="1.10")

    # --- resources ---
    resources = ET.SubElement(root, "resources")
    ET.SubElement(resources, "format", {
        "id": fmt_id,
        "name": _format_name(fps, height),
        "frameDuration": _frame_duration(fps),
        "width": str(width),
        "height": str(height),
    })
    asset = ET.SubElement(resources, "asset", {
        "id": asset_id,
        "name": video_path.stem,
        "uid": asset_uid,
        "start": "0s",
        "duration": _t(total_sec),
        "hasVideo": "1",
        "hasAudio": "1",
        "audioSources": "1",
        "audioChannels": "2",
        "audioRate": "44100",
    })
    # 相対パス: Plugin 側で展開後にフルパスへ書き換える
    ET.SubElement(asset, "media-rep", {
        "kind": "original-media",
        "src": f"./media/{video_path.name}",
    })

    # 字幕スタイル定義
    if segments:
        cs = caption_style or {}
        font_size = str(int(cs.get("font_size", 36)))
        bold = "1" if cs.get("bold", True) else "0"
        font_face = "Bold" if bold == "1" else "Regular"
        font_color = _hex_to_fcpxml_color(str(cs.get("primary_color", "#FFFFFF")))
        shadow_parts = _hex_to_fcpxml_color(str(cs.get("outline_color", "#000000"))).split()
        shadow_color = f"{shadow_parts[0]} {shadow_parts[1]} {shadow_parts[2]} 0.75"

        ts_def = ET.SubElement(resources, "text-style-def", {"id": ts_id})
        ET.SubElement(ts_def, "text-style", {
            "font": ".AppleSystemUIFont",
            "fontSize": font_size,
            "fontFace": font_face,
            "fontColor": font_color,
            "bold": bold,
            "shadowColor": shadow_color,
            "shadowOffset": "5 315",
            "shadowBlurRadius": "4",
            "alignment": "center",
        })

    # テキストオーバーレイ用スタイル
    if texts:
        ts_title_def = ET.SubElement(resources, "text-style-def", {"id": ts_title_id})
        ET.SubElement(ts_title_def, "text-style", {
            "font": ".AppleSystemUIFont",
            "fontSize": "48",
            "fontFace": "Bold",
            "fontColor": "1 1 1 1",
            "bold": "1",
            "shadowColor": "0 0 0 0.75",
            "shadowOffset": "5 315",
            "shadowBlurRadius": "8",
            "alignment": "center",
        })

    # --- library > event > project > sequence > spine ---
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": "EditClone"})
    project_el = ET.SubElement(event, "project", {"name": video_path.stem})
    tc_format = "DF" if abs(fps - 29.97) < 0.05 or abs(fps - 59.94) < 0.05 else "NDF"
    sequence = ET.SubElement(project_el, "sequence", {
        "duration": _t(timeline_dur),
        "format": fmt_id,
        "tcStart": "0s",
        "tcFormat": tc_format,
        "audioLayout": "stereo",
        "audioRate": "44100",
    })
    spine = ET.SubElement(sequence, "spine")

    # カラー補正プリセット情報をメタデータとして埋め込む
    if color:
        note_el = ET.SubElement(spine, "note")
        note_el.text = f"EditClone color preset: {color}"

    # virtual_offset: speed 適用前のタイムライン位置 (字幕タイムスタンプと同じ座標系)
    timeline_offset = 0.0
    virtual_offset = 0.0

    for i, (seg_start, seg_end) in enumerate(kept):
        seg_src_dur = seg_end - seg_start
        seg_out_dur = seg_src_dur / speed

        clip_el = ET.SubElement(spine, "clip", {
            "name": f"{video_path.stem}_{i + 1}",
            "ref": asset_id,
            "offset": _t(timeline_offset),
            "duration": _t(seg_out_dur),
            "start": _t(seg_start),
        })

        # 速度変更 (retime)
        if abs(speed - 1.0) > 0.01:
            retime_el = ET.SubElement(clip_el, "retime", {
                "duration": _t(seg_out_dur),
                "offset": "0s",
                "src": "0s",
            })
            tm = ET.SubElement(retime_el, "timeMap")
            ET.SubElement(tm, "timept", {
                "time": "0s",
                "value": "0s",
                "interp": "smooth2",
            })
            ET.SubElement(tm, "timept", {
                "time": _t(seg_out_dur),
                "value": _t(seg_src_dur),
                "interp": "smooth2",
            })

        # 音量調整
        if audio_db_val is not None:
            ET.SubElement(clip_el, "adjust-volume", {
                "amount": f"{audio_db_val:+.1f}dB",
            })

        # 字幕 caption (lane=-1)
        if segments:
            clip_virtual_end = virtual_offset + seg_src_dur
            for sub in segments:
                sub_vs = float(sub.get("start", 0))
                sub_ve = float(sub.get("end", 0))
                sub_text = str(sub.get("text", "")).strip()
                if not sub_text:
                    continue
                # 仮想タイムラインでオーバーラップを計算
                ov_vs = max(sub_vs, virtual_offset)
                ov_ve = min(sub_ve, clip_virtual_end)
                if ov_ve - ov_vs < 0.05:
                    continue
                # 実タイムラインへ変換 (speed 適用)
                ov_rs = timeline_offset + (ov_vs - virtual_offset) / speed
                ov_re = timeline_offset + (ov_ve - virtual_offset) / speed
                cap_offset = ov_rs - timeline_offset
                cap_dur = ov_re - ov_rs
                cap_el = ET.SubElement(clip_el, "caption", {
                    "lane": "-1",
                    "offset": _t(cap_offset),
                    "duration": _t(max(cap_dur, 0.05)),
                    "role": "iTT:caption.iTT-Subtitle",
                })
                text_el = ET.SubElement(cap_el, "text")
                ts_el = ET.SubElement(text_el, "text-style", {"ref": ts_id})
                ts_el.text = sub_text

        timeline_offset += seg_out_dur
        virtual_offset += seg_src_dur

        # クリップ間トランジション（最後以外）
        if tran_dur > 0 and i < len(kept) - 1:
            ET.SubElement(spine, "transition", {
                "name": "Cross Dissolve",
                "duration": _t(tran_dur),
                "offset": _t(timeline_offset),
            })
            timeline_offset += tran_dur

    # テキストオーバーレイ (lane=1, caption として)
    for txt_op in texts:
        txt_content = str(txt_op.get("text", "")).strip()
        txt_start = float(txt_op.get("start", 0))
        txt_dur = float(txt_op.get("duration", 3.0))
        if not txt_content:
            continue
        cap_el = ET.SubElement(spine, "caption", {
            "lane": "1",
            "offset": _t(txt_start),
            "duration": _t(txt_dur),
            "role": "iTT:caption.iTT-Subtitle",
        })
        text_el = ET.SubElement(cap_el, "text")
        ref = ts_title_id if texts else ts_id
        ts_el = ET.SubElement(text_el, "text-style", {"ref": ref})
        ts_el.text = txt_content

    # pretty-print + DOCTYPE
    raw = ET.tostring(root, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8")
    lines = pretty.decode("utf-8").splitlines()
    lines.insert(1, "<!DOCTYPE fcpxml>")
    return "\n".join(lines)
