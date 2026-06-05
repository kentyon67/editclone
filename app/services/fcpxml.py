import uuid
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

from app.services.cut_suggestion import suggest_cuts
from app.services.video_info import extract_video_info


def _t(seconds: float) -> str:
    """Float秒 → FCPXML有理数時刻文字列 (ms精度)"""
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
) -> str:
    info = extract_video_info(video_path)
    total_sec = info["duration_seconds"] or 0.0
    width = info["width"] or 1920
    height = info["height"] or 1080
    fps = info["fps"] or 30.0
    fps_int = int(round(fps))

    if cuts is None:
        cuts = suggest_cuts(video_path, noise_db=noise_db, min_duration=min_duration)
    kept = _kept_segments(cuts, total_sec)
    timeline_dur = sum(e - s for s, e in kept)

    asset_uid = uuid.uuid4().hex.upper()
    fmt_id = "r1"
    asset_id = "r2"

    root = ET.Element("fcpxml", version="1.10")

    # --- resources ---
    resources = ET.SubElement(root, "resources")
    ET.SubElement(resources, "format", {
        "id": fmt_id,
        "name": f"FFVideoFormat{height}p{fps_int}",
        "frameDuration": f"1/{fps_int}s",
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

    # --- library > event > project > sequence > spine ---
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": "EditClone"})
    project = ET.SubElement(event, "project", {"name": video_path.stem})
    sequence = ET.SubElement(project, "sequence", {
        "duration": _t(timeline_dur),
        "format": fmt_id,
        "tcStart": "0s",
        "tcFormat": "NDF",
        "audioLayout": "stereo",
        "audioRate": "44100",
    })
    spine = ET.SubElement(sequence, "spine")

    timeline_offset = 0.0
    for i, (seg_start, seg_end) in enumerate(kept):
        seg_dur = seg_end - seg_start
        ET.SubElement(spine, "clip", {
            "name": f"{video_path.stem}_{i + 1}",
            "ref": asset_id,
            "offset": _t(timeline_offset),
            "duration": _t(seg_dur),
            "start": _t(seg_start),
        })
        timeline_offset += seg_dur

    # pretty-print + DOCTYPE
    raw = ET.tostring(root, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8")
    lines = pretty.decode("utf-8").splitlines()
    lines.insert(1, "<!DOCTYPE fcpxml>")
    return "\n".join(lines)
