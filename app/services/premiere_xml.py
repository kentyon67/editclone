"""
Premiere Pro 用 XMEML (FCP 7 XML) ジェネレーター。
Premiere Pro は File > Import で .xml を読み込める。
タイムスタンプはフレーム数（整数）で指定する。
"""

import uuid
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET


def _is_ntsc(fps: float) -> bool:
    """29.97 / 23.976 / 59.94 fps は NTSC。"""
    return abs(fps - 29.97) < 0.05 or abs(fps - 23.976) < 0.05 or abs(fps - 59.94) < 0.05


def _fps_int(fps: float) -> int:
    """NTSC は 29.97 → 30, 23.976 → 24 と timebase を整数化する。"""
    return int(round(fps))


def _frames(seconds: float, fps: float) -> int:
    return max(0, int(round(seconds * fps)))


def _kept_segments(cuts: list[dict], total: float) -> list[tuple[float, float]]:
    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for cut in sorted(cuts, key=lambda c: float(c["cut_start"])):
        s, e = float(cut["cut_start"]), float(cut["cut_end"])
        if s > cursor:
            segments.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        segments.append((cursor, total))
    return [(s, e) for s, e in segments if e - s > 0.05]


def _rate_elem(parent: ET.Element, fps: float) -> None:
    r = ET.SubElement(parent, "rate")
    ET.SubElement(r, "timebase").text = str(_fps_int(fps))
    ET.SubElement(r, "ntsc").text = "TRUE" if _is_ntsc(fps) else "FALSE"


def build_premiere_xml(
    video_path: Path,
    cuts: list[dict],
    total_duration: float,
    fps: float = 30.0,
    width: int = 1920,
    height: int = 1080,
) -> str:
    kept = _kept_segments(cuts, total_duration)
    total_frames = _frames(total_duration, fps)
    timeline_total = sum(_frames(e - s, fps) for s, e in kept)

    file_id = f"file-{uuid.uuid4().hex[:8]}"

    xmeml = ET.Element("xmeml", version="5")
    seq = ET.SubElement(xmeml, "sequence", id=f"seq-{uuid.uuid4().hex[:8]}")
    ET.SubElement(seq, "uuid").text = str(uuid.uuid4())
    ET.SubElement(seq, "duration").text = str(timeline_total)
    _rate_elem(seq, fps)
    ET.SubElement(seq, "name").text = f"EditClone - {video_path.stem}"

    media = ET.SubElement(seq, "media")

    # --- Video ---
    video_el = ET.SubElement(media, "video")
    fmt = ET.SubElement(video_el, "format")
    sc = ET.SubElement(fmt, "samplecharacteristics")
    _rate_elem(sc, fps)
    ET.SubElement(sc, "width").text = str(width)
    ET.SubElement(sc, "height").text = str(height)

    v_track = ET.SubElement(video_el, "track")

    # --- Audio ---
    audio_el = ET.SubElement(media, "audio")
    ET.SubElement(audio_el, "numOutputChannels").text = "2"
    afmt = ET.SubElement(audio_el, "format")
    asc = ET.SubElement(afmt, "samplecharacteristics")
    ET.SubElement(asc, "depth").text = "16"
    ET.SubElement(asc, "samplerate").text = "44100"
    a_track = ET.SubElement(audio_el, "track")

    timeline_pos = 0
    first_file = True

    for i, (seg_start, seg_end) in enumerate(kept):
        seg_frames = _frames(seg_end - seg_start, fps)
        in_f = _frames(seg_start, fps)
        out_f = _frames(seg_end, fps)
        clip_id = f"clipitem-{i + 1}"

        def make_clip(track: ET.Element, cid: str) -> ET.Element:
            ci = ET.SubElement(track, "clipitem", id=cid)
            ET.SubElement(ci, "name").text = f"{video_path.stem}_{i + 1}"
            ET.SubElement(ci, "duration").text = str(seg_frames)
            _rate_elem(ci, fps)
            ET.SubElement(ci, "start").text = str(timeline_pos)
            ET.SubElement(ci, "end").text = str(timeline_pos + seg_frames)
            ET.SubElement(ci, "in").text = str(in_f)
            ET.SubElement(ci, "out").text = str(out_f)
            return ci

        # Video clip
        vci = make_clip(v_track, f"v{clip_id}")
        if first_file:
            f_el = ET.SubElement(vci, "file", id=file_id)
            ET.SubElement(f_el, "name").text = video_path.name
            ET.SubElement(f_el, "pathurl").text = (
                f"file://localhost/EDITCLONE_MEDIA/{video_path.name}"
            )
            _rate_elem(f_el, fps)
            ET.SubElement(f_el, "duration").text = str(total_frames)
            tc = ET.SubElement(f_el, "timecode")
            _rate_elem(tc, fps)
            ET.SubElement(tc, "string").text = "00:00:00:00"
            ET.SubElement(tc, "frame").text = "0"
            ET.SubElement(tc, "displayformat").text = "NDF"
            fm = ET.SubElement(f_el, "media")
            fv = ET.SubElement(fm, "video")
            fvsc = ET.SubElement(fv, "samplecharacteristics")
            _rate_elem(fvsc, fps)
            ET.SubElement(fvsc, "width").text = str(width)
            ET.SubElement(fvsc, "height").text = str(height)
            fa = ET.SubElement(fm, "audio")
            fasc = ET.SubElement(fa, "samplecharacteristics")
            ET.SubElement(fasc, "depth").text = "16"
            ET.SubElement(fasc, "samplerate").text = "44100"
            ET.SubElement(fa, "channelcount").text = "2"
            first_file = False
        else:
            ET.SubElement(vci, "file", id=file_id)

        # Audio clip (linked, reference only)
        aci = make_clip(a_track, f"a{clip_id}")
        ET.SubElement(aci, "file", id=file_id)
        ET.SubElement(aci, "trackindex").text = "1"

        timeline_pos += seg_frames

    raw = ET.tostring(xmeml, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8")
    lines = pretty.decode("utf-8").splitlines()
    lines.insert(1, "<!DOCTYPE xmeml>")
    return "\n".join(lines)
