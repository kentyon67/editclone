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


# ---------------------------------------------------------------------------
# Operation helpers
# ---------------------------------------------------------------------------

def _speed_percent(operations: list[dict]) -> int | None:
    for op in (operations or []):
        if op.get("type") == "speed":
            return max(10, int(op.get("speed_percent", 100)))
    return None


def _audio_db(operations: list[dict]) -> float | None:
    for op in (operations or []):
        if op.get("type") == "audio":
            db = op.get("volume_db")
            if db is not None:
                return float(db)
    return None


def _has_transition(operations: list[dict]) -> tuple[bool, float]:
    for op in (operations or []):
        if op.get("type") == "transition":
            return True, max(0.1, float(op.get("duration", 0.5)))
    return False, 0.0


def _text_ops(operations: list[dict]) -> list[dict]:
    return [op for op in (operations or []) if op.get("type") == "text"]


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_premiere_xml(
    video_path: Path,
    cuts: list[dict],
    total_duration: float,
    fps: float = 30.0,
    width: int = 1920,
    height: int = 1080,
    segments: list[dict] | None = None,
    operations: list[dict] | None = None,
) -> str:
    kept = _kept_segments(cuts, total_duration)
    total_frames = _frames(total_duration, fps)

    spd = _speed_percent(operations)
    audio_db_val = _audio_db(operations)
    has_tran, tran_sec = _has_transition(operations)
    texts = _text_ops(operations)

    # 速度が指定されていればタイムライン長を調整
    speed_factor = (spd / 100.0) if spd else 1.0
    timeline_total = sum(
        int(round(_frames(e - s, fps) / speed_factor))
        for s, e in kept
    )

    file_id = f"file-{uuid.uuid4().hex[:8]}"
    tran_frames = _frames(tran_sec, fps) if has_tran else 0

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
        # 速度調整後のフレーム数
        out_frames = int(round(seg_frames / speed_factor))
        in_f = _frames(seg_start, fps)
        out_f = _frames(seg_end, fps)
        clip_id = f"clipitem-{i + 1}"

        def make_clip(track: ET.Element, cid: str) -> ET.Element:
            ci = ET.SubElement(track, "clipitem", id=cid)
            ET.SubElement(ci, "name").text = f"{video_path.stem}_{i + 1}"
            ET.SubElement(ci, "duration").text = str(out_frames)
            _rate_elem(ci, fps)
            ET.SubElement(ci, "start").text = str(timeline_pos)
            ET.SubElement(ci, "end").text = str(timeline_pos + out_frames)
            ET.SubElement(ci, "in").text = str(in_f)
            ET.SubElement(ci, "out").text = str(out_f)
            return ci

        # Video clip
        vci = make_clip(v_track, f"v{clip_id}")
        if first_file:
            f_el = ET.SubElement(vci, "file", id=file_id)
            ET.SubElement(f_el, "name").text = video_path.name
            # 相対パス: Plugin 側で展開後にフルパスへ書き換える
            ET.SubElement(f_el, "pathurl").text = f"./media/{video_path.name}"
            _rate_elem(f_el, fps)
            ET.SubElement(f_el, "duration").text = str(total_frames)
            tc = ET.SubElement(f_el, "timecode")
            _rate_elem(tc, fps)
            ET.SubElement(tc, "string").text = "00:00:00;00" if _is_ntsc(fps) else "00:00:00:00"
            ET.SubElement(tc, "frame").text = "0"
            ET.SubElement(tc, "displayformat").text = "DF" if _is_ntsc(fps) else "NDF"
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

        # 速度設定 (speed_percent 指定時)
        if spd and spd != 100:
            spd_el = ET.SubElement(vci, "speed")
            _rate_elem(spd_el, fps)
            ET.SubElement(spd_el, "percent").text = str(spd)
            ET.SubElement(spd_el, "absolute").text = "FALSE"

        # 音量フィルタ
        if audio_db_val is not None:
            linear_gain = round(10 ** (audio_db_val / 20.0), 4)
            filt_el = ET.SubElement(vci, "filter")
            eff_el = ET.SubElement(filt_el, "effect")
            ET.SubElement(eff_el, "name").text = "Audio Levels"
            ET.SubElement(eff_el, "effectid").text = "audiolevels"
            ET.SubElement(eff_el, "effecttype").text = "filter"
            ET.SubElement(eff_el, "mediatype").text = "audio"
            param_el = ET.SubElement(eff_el, "parameter")
            ET.SubElement(param_el, "parameterid").text = "level"
            ET.SubElement(param_el, "name").text = "Level"
            ET.SubElement(param_el, "value").text = str(linear_gain)

        # Audio clip
        aci = make_clip(a_track, f"a{clip_id}")
        ET.SubElement(aci, "file", id=file_id)
        ET.SubElement(aci, "trackindex").text = "1"

        timeline_pos += out_frames

        # クリップ間トランジション（最後以外）
        if has_tran and tran_frames > 0 and i < len(kept) - 1:
            tran_start = timeline_pos - tran_frames // 2
            tran_end = tran_start + tran_frames
            ti = ET.SubElement(v_track, "transitionitem")
            _rate_elem(ti, fps)
            ET.SubElement(ti, "start").text = str(tran_start)
            ET.SubElement(ti, "end").text = str(tran_end)
            ET.SubElement(ti, "alignment").text = "end-black"
            eff_el = ET.SubElement(ti, "effect")
            ET.SubElement(eff_el, "name").text = "Cross Dissolve"
            ET.SubElement(eff_el, "effectid").text = "Cross Dissolve"
            ET.SubElement(eff_el, "effectcategory").text = "Dissolve"
            ET.SubElement(eff_el, "effecttype").text = "transition"
            ET.SubElement(eff_el, "mediatype").text = "video"

    # 字幕セグメントをシーケンスマーカーとして埋め込む
    if segments:
        for seg in segments:
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            start_f = _frames(float(seg.get("start", 0)), fps)
            dur_f = max(1, _frames(
                float(seg.get("end", 0)) - float(seg.get("start", 0)), fps
            ))
            marker_el = ET.SubElement(seq, "marker")
            ET.SubElement(marker_el, "comment").text = text
            label = text[:28] + "…" if len(text) > 28 else text
            ET.SubElement(marker_el, "name").text = label
            ET.SubElement(marker_el, "in").text = str(start_f)
            ET.SubElement(marker_el, "duration").text = str(dur_f)

    # テキストオーバーレイをマーカーとして埋め込む
    for txt_op in texts:
        txt_content = str(txt_op.get("text", "")).strip()
        txt_start = float(txt_op.get("start", 0))
        txt_dur = float(txt_op.get("duration", 3.0))
        if not txt_content:
            continue
        marker_el = ET.SubElement(seq, "marker")
        ET.SubElement(marker_el, "comment").text = f"[TITLE] {txt_content}"
        ET.SubElement(marker_el, "name").text = txt_content[:28]
        ET.SubElement(marker_el, "in").text = str(_frames(txt_start, fps))
        ET.SubElement(marker_el, "duration").text = str(max(1, _frames(txt_dur, fps)))

    raw = ET.tostring(xmeml, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8")
    lines = pretty.decode("utf-8").splitlines()
    lines.insert(1, "<!DOCTYPE xmeml>")
    return "\n".join(lines)
