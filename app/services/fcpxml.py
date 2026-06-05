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


def build_fcpxml(
    video_path: Path,
    noise_db: float = -30.0,
    min_duration: float = 0.5,
    cuts: list[dict] | None = None,
    video_info: dict | None = None,
    segments: list[dict] | None = None,
) -> str:
    """FCPXML を生成する。segments を渡すと caption lane として字幕を埋め込む。"""
    if video_info is None:
        video_info = extract_video_info(video_path)

    total_sec = float(video_info.get("duration_seconds") or 0.0)
    width = int(video_info.get("width") or 1920)
    height = int(video_info.get("height") or 1080)
    fps = float(video_info.get("fps") or 30.0)

    if cuts is None:
        cuts = suggest_cuts(video_path, noise_db=noise_db, min_duration=min_duration)
    kept = _kept_segments(cuts, total_sec)
    timeline_dur = sum(e - s for s, e in kept)

    asset_uid = uuid.uuid4().hex.upper()
    fmt_id = "r1"
    asset_id = "r2"
    ts_id = "ts1"

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
    ET.SubElement(asset, "media-rep", {
        "kind": "original-media",
        "src": f"file://localhost/EDITCLONE_MEDIA/{video_path.name}",
    })

    # 字幕スタイル定義（segments がある場合のみ追加）
    if segments:
        ts_def = ET.SubElement(resources, "text-style-def", {"id": ts_id})
        ET.SubElement(ts_def, "text-style", {
            "font": ".AppleSystemUIFont",
            "fontSize": "36",
            "fontFace": "Regular",
            "fontColor": "1 1 1 1",
            "bold": "1",
            "shadowColor": "0 0 0 0.75",
            "shadowOffset": "5 315",
            "shadowBlurRadius": "4",
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

    timeline_offset = 0.0
    for i, (seg_start, seg_end) in enumerate(kept):
        seg_dur = seg_end - seg_start
        clip_el = ET.SubElement(spine, "clip", {
            "name": f"{video_path.stem}_{i + 1}",
            "ref": asset_id,
            "offset": _t(timeline_offset),
            "duration": _t(seg_dur),
            "start": _t(seg_start),
        })

        # 字幕 caption を clip の lane=-1 に追加
        if segments:
            clip_tl_end = timeline_offset + seg_dur
            for sub in segments:
                sub_s = float(sub.get("start", 0))
                sub_e = float(sub.get("end", 0))
                sub_text = str(sub.get("text", "")).strip()
                if not sub_text:
                    continue
                overlap_s = max(sub_s, timeline_offset)
                overlap_e = min(sub_e, clip_tl_end)
                if overlap_e - overlap_s < 0.05:
                    continue
                cap_el = ET.SubElement(clip_el, "caption", {
                    "lane": "-1",
                    "offset": _t(overlap_s - timeline_offset),
                    "duration": _t(overlap_e - overlap_s),
                    "role": "iTT:caption.iTT-Subtitle",
                })
                text_el = ET.SubElement(cap_el, "text")
                ts_el = ET.SubElement(text_el, "text-style", {"ref": ts_id})
                ts_el.text = sub_text

        timeline_offset += seg_dur

    # pretty-print + DOCTYPE
    raw = ET.tostring(root, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8")
    lines = pretty.decode("utf-8").splitlines()
    lines.insert(1, "<!DOCTYPE fcpxml>")
    return "\n".join(lines)
