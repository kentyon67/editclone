#!/usr/bin/env python3
"""
EditClone — DaVinci Resolve AI 編集エージェント v4
=================================================
• 🎬 AI編集  — メディアプールからクリップを選択→アップロード→AI処理→タイムライン自動生成
• 💬 チャット — プロンプトで継続的にインタラクティブ編集（カット・速度・音量・字幕・ズーム等）
• 🎨 スタイル — Style Profile 管理・切り替え
• ⚙️ 設定    — API URL / Token / 診断

インストール:
  Windows: %APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility\\
  macOS:   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
"""

import json
import os
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path

# ================================================================
# 設定管理
# ================================================================

_CONFIG_PATH = Path.home() / ".editclone" / "config.json"
_DEFAULT_API_URL = "https://editclone-production.up.railway.app"
_API_URL = ""
_API_TOKEN = ""


def _load_config() -> tuple:
    if _CONFIG_PATH.exists():
        try:
            d = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return d.get("api_url", ""), d.get("api_token", "")
        except Exception:
            pass
    return "", ""


def _save_config(url: str, token: str) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(
        json.dumps({"api_url": url, "api_token": token}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ================================================================
# API ヘルパー
# ================================================================

def _add_auth(req: urllib.request.Request) -> None:
    if not _API_TOKEN:
        return
    if _API_TOKEN.startswith("eck_"):
        req.add_header("X-Api-Key", _API_TOKEN)
    else:
        req.add_header("Authorization", f"Bearer {_API_TOKEN}")


def _api(method: str, endpoint: str, payload=None, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(f"{_API_URL}{endpoint}", data=data, method=method)
    _add_auth(req)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def api_get(ep: str, timeout: int = 30) -> dict:
    return _api("GET", ep, timeout=timeout)


def api_post(ep: str, payload=None, timeout: int = 30) -> dict:
    return _api("POST", ep, payload, timeout=timeout)


def upload_video(file_path: str, on_progress=None) -> str:
    boundary = f"----EC{uuid.uuid4().hex}"
    filename = Path(file_path).name
    if on_progress:
        on_progress("ファイル読み込み中...")
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    size_mb = len(file_bytes) / 1024 / 1024
    if on_progress:
        on_progress(f"アップロード中... ({size_mb:.1f} MB)")
    header = (
        f"--{boundary}\r\nContent-Disposition: form-data; "
        f'name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'
    ).encode()
    body = header + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{_API_URL}/videos/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    _add_auth(req)
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["video_id"]


def download_srt_file(job_id: str) -> str:
    """SRT をローカルに保存してパスを返す。"""
    videos_dir = "Videos" if sys.platform == "win32" else "Movies"
    out_dir = Path.home() / videos_dir / "EditClone" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    srt_path = out_dir / "subtitle.srt"
    req = urllib.request.Request(f"{_API_URL}/plugin/jobs/{job_id}/srt")
    _add_auth(req)
    with urllib.request.urlopen(req, timeout=30) as r:
        srt_path.write_bytes(r.read())
    return str(srt_path)


# ================================================================
# DaVinci Resolve 接続
# ================================================================

_RESOLVE_ERRORS: list = []


def get_resolve():
    _RESOLVE_ERRORS.clear()
    g = globals()
    for name, fn in [("app", lambda o: o.GetResolve()), ("fu", lambda o: o.GetResolve())]:
        obj = g.get(name)
        if obj is not None:
            try:
                r = fn(obj)
                if r:
                    return r
                _RESOLVE_ERRORS.append(f"{name}.GetResolve(): None")
            except Exception as e:
                _RESOLVE_ERRORS.append(f"{name}: {e}")
        else:
            _RESOLVE_ERRORS.append(f"{name}: なし")

    _bmd = g.get("bmd")
    if _bmd:
        for app_name in ("Resolve", "Fusion"):
            try:
                obj = _bmd.scriptapp(app_name)
                if obj:
                    r = obj if app_name == "Resolve" else obj.GetResolve()
                    if r:
                        return r
                    _RESOLVE_ERRORS.append(f"bmd→{app_name}: None")
            except Exception as e:
                _RESOLVE_ERRORS.append(f"bmd→{app_name}: {e}")
    else:
        _RESOLVE_ERRORS.append("bmd: なし")

    for path in [
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules",
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve",
        "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/",
        "/opt/resolve/Developer/Scripting/Modules/",
    ]:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    try:
        import DaVinciResolveScript as dvr  # type: ignore
        r = dvr.scriptapp("Resolve")
        if r:
            return r
        _RESOLVE_ERRORS.append("DaVinciResolveScript: None")
    except Exception as e:
        _RESOLVE_ERRORS.append(f"DaVinciResolveScript: {e}")
    return None


# ================================================================
# DaVinci 操作ヘルパー
# ================================================================

def get_media_pool_clips(resolve) -> list:
    try:
        project = resolve.GetProjectManager().GetCurrentProject()
        if not project:
            return []
        root = project.GetMediaPool().GetRootFolder()
        clips = []

        def collect(folder):
            for c in (folder.GetClipList() or []):
                clips.append(c)
            for sub in (folder.GetSubFolderList() or []):
                collect(sub)

        collect(root)
        return clips
    except Exception:
        return []


def cuts_to_keep_segments(cuts: list, total_duration: float) -> list:
    """
    カット（削除）セグメント [{"cut_start":s,"cut_end":e},...] から
    保持セグメント [{"start":s,"end":e},...] を計算して返す。
    ジョブ結果の cuts フォーマット(cut_start/cut_end)とチャット操作の
    keep_segments フォーマット(start/end)の両方を自動判定する。
    """
    if not cuts:
        return [{"start": 0.0, "end": total_duration}] if total_duration > 0 else []

    # keep_segments 形式 (start/end) が既に渡された場合はそのまま返す
    if "start" in cuts[0] or "end" in cuts[0]:
        return cuts

    # cut_start/cut_end 形式から保持区間を算出
    kept = []
    cursor = 0.0
    for cut in sorted(cuts, key=lambda c: float(c.get("cut_start", 0))):
        s = float(cut.get("cut_start", 0))
        e = float(cut.get("cut_end", 0))
        if s > cursor + 0.05:
            kept.append({"start": round(cursor, 3), "end": round(s, 3)})
        cursor = max(cursor, e)
    if total_duration > 0 and cursor < total_duration - 0.05:
        kept.append({"start": round(cursor, 3), "end": round(total_duration, 3)})
    return kept


def apply_cuts_to_timeline(resolve, media_clip, cuts: list, fps: float, name: str,
                           total_duration: float = 0.0):
    """
    cuts には keep_segments 形式(start/end) または job cuts 形式(cut_start/cut_end) を渡せる。
    どちらも自動判定して正しいタイムラインを生成する。
    """
    project = resolve.GetProjectManager().GetCurrentProject()
    if not project:
        return None, "アクティブなプロジェクトがありません"
    media_pool = project.GetMediaPool()

    # フォーマット統一
    keep_segs = cuts_to_keep_segments(cuts, total_duration)

    infos = []
    for seg in keep_segs:
        sf = round(float(seg.get("start", 0)) * fps)
        ef = round(float(seg.get("end",   0)) * fps)
        if ef > sf:
            infos.append({"mediaPoolItem": media_clip, "startFrame": sf,
                          "endFrame": ef, "mediaType": 1})
    if not infos:
        return None, "有効なセグメントがありません"
    tl = media_pool.CreateTimelineFromClips(name, infos)
    if not tl:
        return None, "CreateTimelineFromClips 失敗"
    project.SetCurrentTimeline(tl)
    return tl, "ok"


def get_source_clip_from_current_timeline(resolve):
    """現在のタイムラインの最初のビデオクリップのメディアプールアイテムを返す。"""
    try:
        project = resolve.GetProjectManager().GetCurrentProject()
        tl = project.GetCurrentTimeline()
        if not tl:
            return None
        items = tl.GetItemsInTrack("video", 1) or {}
        first = next(iter(items.values())) if items else None
        return first.GetMediaPoolItem() if first else None
    except Exception:
        return None


# ================================================================
# 編集操作の適用（全タイプ対応）
# ================================================================

def _get_current_timeline(resolve):
    try:
        return resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    except Exception:
        return None


def _get_video_items(tl):
    items = {}
    try:
        cnt = tl.GetTrackCount("video")
        for i in range(1, cnt + 1):
            items.update(tl.GetItemsInTrack("video", i) or {})
    except Exception:
        pass
    return items


def _get_audio_items(tl):
    items = {}
    try:
        cnt = tl.GetTrackCount("audio")
        for i in range(1, cnt + 1):
            items.update(tl.GetItemsInTrack("audio", i) or {})
    except Exception:
        pass
    return items


def apply_single_operation(resolve, op: dict, job_ctx: dict, source_clip) -> tuple:
    """
    1 つの操作を DaVinci に適用。
    返り値: (icon, message)  icon = "✓"|"⚠"|"✗"
    """
    op_type = op.get("type", "")
    desc    = op.get("description", op_type)

    # ── カット構成変更 ──────────────────────────────────────
    if op_type == "cut":
        segs = op.get("keep_segments") or []
        if not segs:
            return "⚠", "keep_segments が空です"
        fps  = float(job_ctx.get("fps", 30))
        dur  = float(job_ctx.get("duration", 0))
        clip = source_clip or get_source_clip_from_current_timeline(resolve)
        if not clip:
            return "✗", "ソースクリップが見つかりません（メディアプールにクリップが必要）"
        tl_name = f"EditClone_{int(time.time()) % 10000}"
        _, result = apply_cuts_to_timeline(resolve, clip, segs, fps, tl_name,
                                           total_duration=dur)
        if result == "ok":
            return "✓", f"タイムライン作成: {len(segs)} セグメント"
        return "✗", result

    # ── トリム（冒頭/末尾削除） ────────────────────────────
    if op_type == "trim":
        start_s  = float(op.get("start_seconds", 0))
        end_s    = float(op.get("end_seconds",   0))
        duration = float(job_ctx.get("duration", 0))
        raw_cuts = job_ctx.get("cuts") or []
        # cut_start/cut_end 形式 → start/end 形式に変換
        keep_segs = cuts_to_keep_segments(raw_cuts, duration)
        if not keep_segs and duration > 0:
            keep_segs = [{"start": 0.0, "end": duration}]
        new_segs = []
        for seg in keep_segs:
            s = max(float(seg["start"]), start_s)
            e = min(float(seg["end"]), duration - end_s) if end_s > 0 else float(seg["end"])
            if e > s + 0.05:
                new_segs.append({"start": s, "end": e})
        if not new_segs:
            return "⚠", "トリム後にセグメントが残りません"
        return apply_single_operation(resolve, {"type": "cut", "keep_segments": new_segs}, job_ctx, source_clip)

    # ── 再生速度 ───────────────────────────────────────────
    if op_type == "speed":
        speed_pct = float(op.get("speed_percent", 100))
        speed_val = speed_pct / 100.0
        tl = _get_current_timeline(resolve)
        if not tl:
            return "✗", "タイムラインがありません"
        applied = 0
        for item in _get_video_items(tl).values():
            try:
                item.SetProperty("Speed", speed_val)
                applied += 1
            except Exception:
                pass
        if applied:
            return "✓", f"速度を {speed_pct:.0f}% に設定 ({applied} クリップ)"
        return "⚠", f"速度変更 API 未対応（DaVinci で手動: クリップ右クリック → Change Speed → {speed_pct:.0f}%）"

    # ── 音量調整 ───────────────────────────────────────────
    if op_type in ("audio", "volume"):
        vol_db = float(op.get("volume_db", 0))
        tl = _get_current_timeline(resolve)
        if not tl:
            return "✗", "タイムラインがありません"
        applied = 0
        for item in _get_audio_items(tl).values():
            for method in ["SetVolume", "SetProperty"]:
                try:
                    if method == "SetVolume":
                        item.SetVolume(vol_db)
                    else:
                        item.SetProperty("Volume", vol_db)
                    applied += 1
                    break
                except Exception:
                    pass
        if applied:
            return "✓", f"音量 {vol_db:+.0f}dB を設定 ({applied} クリップ)"
        return "⚠", f"音量変更 API 未対応（DaVinci Fairlight で手動: {vol_db:+.0f}dB）"

    # ── ズーム ─────────────────────────────────────────────
    if op_type == "zoom":
        zoom = float(op.get("zoom_level", 1.0))
        tl = _get_current_timeline(resolve)
        if not tl:
            return "✗", "タイムラインがありません"
        applied = 0
        for item in _get_video_items(tl).values():
            try:
                item.SetProperty("ZoomX", zoom)
                item.SetProperty("ZoomY", zoom)
                applied += 1
            except Exception:
                pass
        if applied:
            return "✓", f"ズーム {zoom:.2f}x を設定 ({applied} クリップ)"
        return "⚠", f"ズーム API 未対応（DaVinci Inspector で手動: {zoom:.2f}x）"

    # ── 字幕追加 ───────────────────────────────────────────
    if op_type == "subtitle":
        job_id = job_ctx.get("job_id", "")
        if not job_id:
            return "✗", "ジョブIDがありません"
        if not job_ctx.get("srt_available"):
            return "⚠", "字幕データが生成されていません（Web でジョブを再処理してください）"
        try:
            srt_path = download_srt_file(job_id)
            project = resolve.GetProjectManager().GetCurrentProject()
            if not project:
                return "✗", "プロジェクトがありません"
            media_pool = project.GetMediaPool()
            clips = media_pool.ImportMedia([srt_path])
            if clips:
                tl = _get_current_timeline(resolve)
                # DaVinci 18.5+ の場合はサブタイトルトラックに追加試行
                if tl:
                    try:
                        tl.InsertSubtitleToTimeline({"mediaPoolItem": clips[0],
                                                     "trackIndex": 1, "recordFrame": 0})
                        return "✓", f"字幕をタイムラインに追加しました"
                    except Exception:
                        pass
                return "✓", f"SRT をメディアプールにインポートしました: {Path(srt_path).name}\n" \
                             "Media Pool から字幕トラックにドラッグしてください"
            return "⚠", "SRT のインポートに失敗しました"
        except Exception as e:
            return "✗", f"字幕取得エラー: {e}"

    # ── カラー調整 ─────────────────────────────────────────
    if op_type == "color":
        preset = op.get("preset", "")
        tl = _get_current_timeline(resolve)
        if tl:
            color_map = {
                "warm": "Orange", "cool": "Blue", "cinematic": "Purple",
                "bright": "Yellow", "dark": "Navy", "bw": "Beige",
            }
            flag = color_map.get(preset, "Pink")
            try:
                for item in _get_video_items(tl).values():
                    item.AddFlag(flag)
            except Exception:
                pass
        # カラーページへ自動遷移
        try:
            resolve.OpenPage("color")
        except Exception:
            pass
        instructions = {
            "warm":      "Color Wheels: Lift/Gamma/Gain を橙寄りに、Saturation +10",
            "cool":      "Color Wheels: Lift/Gamma/Gain を青寄りに、Saturation -5",
            "cinematic": "Curves: S字コントラスト、Saturation -15、Lift +5",
            "bright":    "Gamma +0.1、Lift +0.05、Gain +0.05",
            "dark":      "Gamma -0.1、Lift -0.05",
            "bw":        "Saturation を 0 に設定",
        }
        msg = instructions.get(preset, f"preset={preset}")
        return "⚠", f"カラー({preset}): Color ページを開きました — {msg}"

    # ── BGM ───────────────────────────────────────────────
    if op_type == "bgm":
        mood = op.get("mood", "")
        return "⚠", (
            f"BGM({mood}): 著作権フリー音楽を検索して追加してください\n"
            "推奨: YouTube Audio Library / Pixabay Music\n"
            "Fairlight ページのオーディオトラックにドラッグ → 音量 -20〜-15dB"
        )

    # ── マーカー追加 ───────────────────────────────────────
    if op_type == "marker":
        moments = op.get("moments") or []
        if not moments:
            return "⚠", "マーカー情報がありません"
        tl = _get_current_timeline(resolve)
        if not tl:
            return "✗", "タイムラインがありません"
        fps = float(job_ctx.get("fps", 30))
        added = 0
        colors = ["Yellow", "Green", "Cyan", "Blue", "Purple", "Red"]
        for i, m in enumerate(moments):
            t     = float(m.get("time", 0))
            label = str(m.get("label", f"Point {i+1}"))
            frame = int(t * fps)
            color = colors[i % len(colors)]
            try:
                tl.AddMarker(frame, color, label, "", 1)
                added += 1
            except Exception:
                pass
        if added:
            return "✓", f"マーカーを {added} 件追加しました"
        return "⚠", "マーカー追加 API 未対応"

    # ── 不明な操作 ─────────────────────────────────────────
    if op_type == "error":
        return "✗", desc
    return "⚠", f"未対応の操作: {op_type} — {desc}"


def apply_all_operations(resolve, operations: list, job_ctx: dict,
                         source_clip, append_cb) -> None:
    """全操作を順に適用し、結果を append_cb でチャットに追記する。"""
    for op in operations:
        op_type = op.get("type", "?")
        try:
            icon, msg = apply_single_operation(resolve, op, job_ctx, source_clip)
        except Exception as e:
            icon, msg = "✗", str(e)
        append_cb("system", f"{icon} [{op_type}] {msg}")
        time.sleep(0.1)


# ================================================================
# GUI
# ================================================================

def run_gui():
    global _API_URL, _API_TOKEN

    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except ImportError:
        print("[EditClone] tkinter が利用できません")
        return

    resolve = get_resolve()

    # テーマ色
    BG     = "#0f0f14"
    BG2    = "#1a1a24"
    BG3    = "#22222e"
    BORDER = "#2e2e3e"
    PURPLE = "#a855f7"
    TEXT   = "#e8e8f0"
    MUTED  = "#8888a8"
    GREEN  = "#22c55e"
    RED    = "#ef4444"
    YELLOW = "#eab308"

    root = tk.Tk()
    root.title("EditClone Agent — DaVinci Resolve")
    root.configure(bg=BG)
    root.geometry("500x720")
    root.resizable(True, True)

    sty = ttk.Style(root)
    sty.theme_use("clam")
    sty.configure(".", background=BG, foreground=TEXT, font=("Helvetica", 11))
    sty.configure("TNotebook", background=BG2, borderwidth=0)
    sty.configure("TNotebook.Tab", background=BG3, foreground=MUTED, padding=[12, 6], borderwidth=0)
    sty.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", PURPLE)])
    sty.configure("TFrame", background=BG)
    sty.configure("TLabel", background=BG, foreground=TEXT)
    sty.configure("TEntry", fieldbackground=BG2, foreground=TEXT, borderwidth=1)
    sty.configure("TCombobox", fieldbackground=BG2, foreground=TEXT)
    sty.configure("TButton", background=BG3, foreground=TEXT, borderwidth=0, padding=[8, 4])
    sty.map("TButton", background=[("active", BG2)], foreground=[("active", PURPLE)])
    sty.configure("P.TButton", background=PURPLE, foreground="#fff")
    sty.map("P.TButton", background=[("active", "#7c3aed")])
    sty.configure("B.TButton", background="#2563eb", foreground="#fff")
    sty.map("B.TButton", background=[("active", "#1d4ed8")])
    sty.configure("TProgressbar", troughcolor=BG3, background=PURPLE, borderwidth=0, thickness=5)
    sty.configure("Treeview", background=BG2, foreground=TEXT, fieldbackground=BG2,
                  rowheight=26, borderwidth=0)
    sty.map("Treeview", background=[("selected", BG3)], foreground=[("selected", PURPLE)])
    sty.configure("Treeview.Heading", background=BG3, foreground=MUTED, borderwidth=0)

    # ── ヘッダー ──────────────────────────────────────────
    header = tk.Frame(root, bg=BG2, height=44)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)
    tk.Label(header, text="✦ EditClone Agent", bg=BG2, fg=PURPLE,
             font=("Helvetica", 13, "bold")).pack(side="left", padx=14, pady=10)
    conn_lbl = tk.Label(
        header,
        text="✓ DaVinci 接続済み" if resolve else "✗ DaVinci 未接続",
        bg=BG2, fg=GREEN if resolve else RED, font=("Helvetica", 9),
    )
    conn_lbl.pack(side="right", padx=14)

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    # 共有状態
    _state: dict = {
        "job_id": "",
        "project_id": "",
        "fps": 30.0,
        "duration": 0.0,
        "cuts": [],
        "srt_available": False,
        "source_clip": None,        # DaVinci media pool item
        "direct_file_path": "",     # ファイルピッカーで直接選択したパス
    }
    styles_data: list = []
    jobs_data: list = []
    _chat_history: list = []  # [{"role":"user"|"assistant","content":str}]

    def st_set(key, val):
        _state[key] = val

    # ================================================================
    # タブ1: 🎬 AI編集
    # ================================================================
    tab_edit = ttk.Frame(nb)
    nb.add(tab_edit, text="🎬 AI編集")

    _clips: list = []

    def _mk_label(parent, text, pady=(0, 2)):
        tk.Label(parent, text=text, bg=BG, fg=MUTED,
                 font=("Helvetica", 10)).pack(anchor="w", padx=12, pady=pady)

    # ── ファイル選択行 ─────────────────────────────────────────
    _mk_label(tab_edit, "① 編集する動画を選択:", pady=(12, 2))

    # 「ファイルを選択」ボタン（最も目立つ操作）
    def _open_file_dialog():
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="編集する動画ファイルを選択",
            filetypes=[
                ("動画ファイル", "*.mp4 *.mov *.avi *.mkv *.mxf *.m4v *.wmv *.MP4 *.MOV"),
                ("すべてのファイル", "*.*"),
            ],
            parent=root,
        )
        if not path:
            return
        # DaVinci が接続済みならメディアプールにインポートを試みる
        if resolve:
            try:
                project = resolve.GetProjectManager().GetCurrentProject()
                if project:
                    mp = project.GetMediaPool()
                    imported = mp.ImportMedia([path])
                    if imported:  # 空リストや None は失敗とみなしフォールスルー
                        _reload_clips()
                        # インポートしたクリップを自動選択
                        for i, c in enumerate(_clips):
                            try:
                                fp = (c.GetClipProperty() or {}).get("File Path", "")
                                if Path(fp).resolve() == Path(path).resolve():
                                    clip_cb.current(i)
                                    _show_clip_info()
                                    break
                            except Exception:
                                pass
                        else:
                            if _clips:
                                clip_cb.current(len(_clips) - 1)
                                _show_clip_info()
                        clip_info_lbl.configure(
                            text="✓ DaVinci メディアプールにインポートしました",
                            fg=GREEN,
                        )
                        return
                    # ImportMedia が空リスト返却 = DaVinci 側でインポート拒否
                    # → direct_file_path フォールバックに継続
            except Exception:
                pass
        # DaVinci 未接続またはインポート失敗 → 直接パスをセット
        _state["direct_file_path"] = path
        fname = Path(path).name
        existing = list(clip_cb["values"])
        if existing == ["クリップなし"] or existing == ["DaVinci 未接続"] or existing == [""]:
            existing = []
        existing.append(fname)
        clip_cb["values"] = existing
        clip_cb.current(len(existing) - 1)
        clip_info_lbl.configure(
            text=f"📂 {fname}  （ファイルから直接読み込み）",
            fg=MUTED,
        )

    btn_file = ttk.Button(tab_edit, text="📂 ファイルを選択...",
                          command=_open_file_dialog)
    btn_file.pack(fill="x", padx=12, pady=(0, 6))

    # メディアプールからの選択（サブ操作）
    clip_row = tk.Frame(tab_edit, bg=BG)
    clip_row.pack(fill="x", padx=12, pady=(0, 2))
    tk.Label(clip_row, text="または メディアプールから:", bg=BG, fg=MUTED,
             font=("Helvetica", 9)).pack(side="left", padx=(0, 6))
    clip_var = tk.StringVar()
    clip_cb  = ttk.Combobox(clip_row, textvariable=clip_var, state="readonly",
                             font=("Helvetica", 10))
    clip_cb.pack(side="left", fill="x", expand=True, padx=(0, 6))

    clip_info_lbl = tk.Label(tab_edit, text="", bg=BG, fg=MUTED,
                             font=("Helvetica", 8), wraplength=460)
    clip_info_lbl.pack(anchor="w", padx=12, pady=(0, 4))

    def _reload_clips():
        nonlocal _clips
        _clips = get_media_pool_clips(resolve) if resolve else []
        names = []
        for c in _clips:
            try:
                p = c.GetClipProperty() or {}
                nm = p.get("Clip Name") or p.get("File Name") or "Unknown"
                du = p.get("Duration", "")
                names.append(f"{nm}  [{du}]" if du else nm)
            except Exception:
                names.append("(取得失敗)")
        if names:
            clip_cb["values"] = names
            clip_cb.current(0)
            _show_clip_info()
        elif resolve:
            clip_cb["values"] = ["（メディアプールにクリップなし）"]
            clip_cb.current(0)
            clip_info_lbl.configure(
                text="↑「ファイルを選択...」ボタンで動画を直接選択できます",
                fg=YELLOW,
            )
        else:
            clip_cb["values"] = ["（DaVinci 未接続）"]
            clip_cb.current(0)

    def _show_clip_info(*_):
        idx = clip_cb.current()
        if idx < 0 or idx >= len(_clips):
            return
        try:
            p    = _clips[idx].GetClipProperty() or {}
            path = p.get("File Path", "パス不明")
            fps  = p.get("FPS", "?")
            res  = p.get("Resolution", "?")
            sz   = p.get("File Size", "")
            clip_info_lbl.configure(
                text=f"📂 {Path(path).name}  |  {fps}fps  |  {res}" +
                     (f"  |  {sz}" if sz else ""),
                fg=MUTED,
            )
            _state["direct_file_path"] = ""  # メディアプール選択時はリセット
        except Exception:
            clip_info_lbl.configure(text="")

    clip_cb.bind("<<ComboboxSelected>>", _show_clip_info)
    ttk.Button(clip_row, text="↻", width=3, command=_reload_clips).pack(side="left")

    ttk.Separator(tab_edit).pack(fill="x", padx=12, pady=8)
    _mk_label(tab_edit, "② 編集指示:")

    PLACEHOLDER = "例: フィラー・無音を除去してテンポよく編集、字幕も追加"
    prompt_box = tk.Text(tab_edit, height=4, bg=BG2, fg=MUTED, insertbackground=TEXT,
                         relief="flat", font=("Helvetica", 11), wrap="word",
                         borderwidth=1, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=PURPLE)
    prompt_box.pack(fill="x", padx=12, pady=(0, 6))
    prompt_box.insert("1.0", PLACEHOLDER)

    def _pin(*_):
        if prompt_box.cget("fg") == MUTED:
            prompt_box.delete("1.0", "end")
            prompt_box.configure(fg=TEXT)

    def _pout(*_):
        if not prompt_box.get("1.0", "end").strip():
            prompt_box.insert("1.0", PLACEHOLDER)
            prompt_box.configure(fg=MUTED)

    prompt_box.bind("<FocusIn>", _pin)
    prompt_box.bind("<FocusOut>", _pout)

    qf = tk.Frame(tab_edit, bg=BG)
    qf.pack(fill="x", padx=12, pady=(0, 8))
    for lbl, pt in [
        ("フィラー除去", "えー・あの・まあ等フィラーと無音をすべてカット"),
        ("テンポアップ", "沈黙・間延びを積極的カットしてテンポアップ"),
        ("Shorts用",    "YouTube Shorts向け: フィラーなし・テンポよく・字幕付き"),
        ("冒頭カット",  "冒頭の挨拶・タイトルコールをカット"),
    ]:
        tk.Button(qf, text=lbl, bg=BG3, fg=MUTED, relief="flat",
                  font=("Helvetica", 9), cursor="hand2", padx=5, pady=2,
                  command=lambda p=pt: (
                      prompt_box.configure(fg=TEXT),
                      prompt_box.delete("1.0", "end"),
                      prompt_box.insert("1.0", p),
                  )).pack(side="left", padx=2)

    # スタイル選択
    sr = tk.Frame(tab_edit, bg=BG)
    sr.pack(fill="x", padx=12, pady=(0, 10))
    tk.Label(sr, text="スタイル:", bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(side="left", padx=(0, 6))
    style_var = tk.StringVar(value="なし（デフォルト）")
    style_combo = ttk.Combobox(sr, textvariable=style_var, state="readonly",
                                font=("Helvetica", 9), width=30)
    style_combo["values"] = ["なし（デフォルト）"]
    style_combo.current(0)
    style_combo.pack(side="left")

    edit_status = tk.Label(tab_edit, text="↑ 動画ファイルを選択して「AIで編集」をクリック",
                           bg=BG, fg=MUTED, font=("Helvetica", 9), wraplength=460)
    edit_status.pack(fill="x", padx=12, pady=(0, 4))
    edit_progress = ttk.Progressbar(tab_edit, mode="indeterminate")
    edit_progress.pack(fill="x", padx=12, pady=(0, 8))

    result_lbl = tk.Label(tab_edit, text="", bg=BG2, fg=MUTED,
                          font=("Helvetica", 10), wraplength=460, justify="left",
                          pady=6, padx=8)
    result_lbl.pack(fill="x", padx=12, pady=(0, 8))

    def _set_est(msg, fg=MUTED):
        edit_status.configure(text=msg, fg=fg)
        edit_status.update_idletasks()

    def _run_ai_edit():
        if not _API_URL or not _API_TOKEN:
            messagebox.showwarning("設定不足", "設定タブで API URL と Token を入力してください",
                                   parent=root)
            nb.select(tab_settings)
            return

        # ファイルパスの決定: ファイルピッカー優先 → メディアプールクリップ
        file_path   = _state.get("direct_file_path", "")
        media_clip  = None

        if not file_path:
            idx = clip_cb.current()
            if idx < 0 or idx >= len(_clips):
                messagebox.showwarning(
                    "動画未選択",
                    "「📂 ファイルを選択...」ボタンで動画ファイルを選んでください",
                    parent=root,
                )
                return
            media_clip = _clips[idx]
            try:
                props     = media_clip.GetClipProperty() or {}
                file_path = props.get("File Path", "")
            except Exception:
                file_path = ""

        if not file_path or not Path(file_path).exists():
            messagebox.showerror("ファイルエラー",
                                 f"ファイルが見つかりません:\n{file_path}", parent=root)
            return

        # プロンプト・スタイル取得（_worker が閉じる前に外スコープで確定させる）
        prompt = prompt_box.get("1.0", "end").strip()
        if prompt == PLACEHOLDER:
            prompt = ""
        s_idx  = style_combo.current()
        prof_id = styles_data[s_idx - 1].get("id", "") if s_idx > 0 and s_idx - 1 < len(styles_data) else ""

        btn_run.configure(state="disabled", text="処理中...")
        edit_progress.start(10)
        result_lbl.configure(text="処理中...", fg=MUTED)

        def _worker():
            try:
                video_id = upload_video(file_path, on_progress=_set_est)
                _set_est("AI処理を開始中...")
                job_id = _api("POST", f"/videos/process/{video_id}",
                              {"prompt": prompt, "style_profile_id": prof_id} if prof_id else
                              {"prompt": prompt},
                              timeout=30)["job_id"]
                _set_est("AI編集中... (1〜3分)")
                for _ in range(180):
                    time.sleep(3)
                    resp   = api_get(f"/jobs/{job_id}")
                    status = resp.get("status", "")
                    prog   = resp.get("progress", "")
                    if prog:
                        _set_est(f"処理中: {prog}")
                    if status == "completed":
                        break
                    if status == "failed":
                        raise RuntimeError(resp.get("error_message") or "処理失敗")
                else:
                    raise RuntimeError("タイムアウト")

                _set_est("カット情報取得中...")
                details    = api_get(f"/plugin/jobs/{job_id}/details")
                cuts       = details.get("cuts") or []
                fps        = float(details.get("fps") or 30)
                dur        = float(details.get("duration") or 0)
                srt_ok     = details.get("srt_available", False)
                project_id = details.get("project_id") or ""

                _set_est("DaVinci タイムラインを生成中...")
                # media_clip が None の場合（ファイル直接選択）はメディアプールにインポート
                if media_clip is None and resolve:
                    try:
                        project = resolve.GetProjectManager().GetCurrentProject()
                        if project:
                            imported = project.GetMediaPool().ImportMedia([file_path])
                            if imported:
                                media_clip = imported[0]
                    except Exception:
                        pass

                clip_name = Path(file_path).stem if not media_clip else ""
                if media_clip:
                    try:
                        clip_name = (media_clip.GetClipProperty() or {}).get("Clip Name", "") or Path(file_path).stem
                    except Exception:
                        clip_name = Path(file_path).stem
                tl_name = f"EditClone_{clip_name[:18]}"

                if media_clip and resolve:
                    _, result = apply_cuts_to_timeline(resolve, media_clip, cuts, fps, tl_name,
                                                       total_duration=dur)
                    if result != "ok":
                        raise RuntimeError(f"タイムライン生成失敗: {result}")
                else:
                    result = "ok (タイムライン生成スキップ: DaVinci未接続)"

                # 状態更新
                st_set("job_id",             job_id)
                st_set("project_id",         project_id)
                st_set("fps",                fps)
                st_set("duration",           dur)
                st_set("cuts",               cuts)
                st_set("srt_available",      srt_ok)
                st_set("source_clip",        media_clip)
                st_set("direct_file_path",   "")  # リセット

                # 会話履歴をリセット
                _chat_history.clear()

                n = len(cuts)
                has_tl = media_clip and resolve
                _set_est(f"✓ 完了！{n} セグメント", GREEN)
                root.after(0, lambda: result_lbl.configure(
                    text=(
                        f"✓ タイムライン「{tl_name}」を作成\n"
                        f"セグメント: {n}  FPS: {fps}  時間: {dur:.1f}s\n"
                        "💬 チャットタブでさらに編集できます"
                        if has_tl else
                        f"✓ AI編集完了（{n} セグメント）\n"
                        "DaVinci が接続されていないためタイムライン生成をスキップしました\n"
                        "設定タブで接続後、チャットタブから操作できます"
                    ),
                    fg=GREEN,
                ))
                root.after(0, lambda: nb.select(tab_chat))

                # ジョブ履歴更新
                threading.Thread(target=_load_jobs, daemon=True).start()

            except Exception as e:
                _set_est(f"エラー: {e}", RED)
                root.after(0, lambda err=e: (
                    result_lbl.configure(text=str(err), fg=RED),
                    messagebox.showerror("エラー", str(err), parent=root),
                ))
            finally:
                root.after(0, lambda: (
                    edit_progress.stop(),
                    btn_run.configure(state="normal", text="🤖 AIで編集"),
                ))

        threading.Thread(target=_worker, daemon=True).start()

    btn_run = ttk.Button(tab_edit, text="🤖 AIで編集",
                         style="P.TButton", command=_run_ai_edit)
    btn_run.pack(fill="x", padx=12, pady=(0, 4))
    ttk.Button(tab_edit, text="↻ クリップリストを更新",
               command=_reload_clips).pack(fill="x", padx=12, pady=(0, 12))

    # ================================================================
    # タブ2: 💬 チャット（インタラクティブ編集）
    # ================================================================
    tab_chat = ttk.Frame(nb)
    nb.add(tab_chat, text="💬 チャット")

    # ジョブ選択バー
    job_row = tk.Frame(tab_chat, bg=BG2, height=36)
    job_row.pack(fill="x")
    job_row.pack_propagate(False)
    tk.Label(job_row, text="ジョブ:", bg=BG2, fg=MUTED,
             font=("Helvetica", 9)).pack(side="left", padx=(10, 4), pady=8)
    job_sel_var = tk.StringVar(value="─ AI編集タブで処理すると自動設定 ─")
    job_sel_cb  = ttk.Combobox(job_row, textvariable=job_sel_var, state="readonly",
                                font=("Helvetica", 9), width=38)
    job_sel_cb["values"] = ["─ AI編集タブで処理すると自動設定 ─"]
    job_sel_cb.current(0)
    job_sel_cb.pack(side="left", padx=(0, 6), pady=4)

    def _on_job_sel(*_):
        idx = job_sel_cb.current()
        if idx <= 0 or idx - 1 >= len(jobs_data):
            return
        j = jobs_data[idx - 1]
        job_id = j["job_id"]
        st_set("job_id",        job_id)
        st_set("project_id",    j.get("project_id", ""))
        st_set("fps",           float(j.get("fps", 30)))
        st_set("duration",      float(j.get("duration", 0)))
        st_set("cuts",          [])
        st_set("srt_available", False)
        st_set("source_clip",   None)
        st_set("direct_file_path", "")
        _chat_history.clear()
        _pending_ops_for_fcpxml.clear()
        root.after(0, lambda: btn_import_fcpxml.pack_forget())
        name = j.get("video_name") or j.get("filename", "不明")
        dur  = float(j.get("duration", 0))
        fps  = float(j.get("fps", 30))
        _append_chat("system", f"ℹ ジョブ「{name}」を選択しました ({dur:.1f}秒 / {fps:.2f}fps)\n指示を入力してください。")

        # バックグラウンドで詳細を取得（srt_available・cuts・project_id を正確にセット）
        def _fetch_details():
            try:
                det = api_get(f"/plugin/jobs/{job_id}/details")
                if _state.get("job_id") != job_id:
                    return  # 別のジョブに切り替わっていたら無視
                st_set("cuts",          det.get("cuts") or [])
                st_set("fps",           float(det.get("fps") or fps))
                st_set("duration",      float(det.get("duration") or dur))
                st_set("srt_available", bool(det.get("srt_available")))
                st_set("project_id",    det.get("project_id") or "")
                srt_ok = bool(det.get("srt_available"))
                _append_chat("system", f"ℹ 詳細読み込み完了 — 字幕: {'あり' if srt_ok else 'なし'}")
            except Exception:
                pass
        threading.Thread(target=_fetch_details, daemon=True).start()

    job_sel_cb.bind("<<ComboboxSelected>>", _on_job_sel)

    # チャット表示エリア
    chat_frame = tk.Frame(tab_chat, bg=BG)
    chat_frame.pack(fill="both", expand=True, padx=6, pady=(4, 0))

    chat_text = tk.Text(
        chat_frame,
        state="disabled",
        bg=BG,
        fg=TEXT,
        font=("Helvetica", 10),
        relief="flat",
        wrap="word",
        spacing1=2,
        spacing3=4,
        padx=8,
        pady=4,
    )
    chat_scroll = ttk.Scrollbar(chat_frame, orient="vertical", command=chat_text.yview)
    chat_text.configure(yscrollcommand=chat_scroll.set)
    chat_scroll.pack(side="right", fill="y")
    chat_text.pack(fill="both", expand=True)

    # タグ定義
    chat_text.tag_config("user_name",  foreground=PURPLE, font=("Helvetica", 9, "bold"))
    chat_text.tag_config("user_msg",   foreground=TEXT,   lmargin1=8, lmargin2=8)
    chat_text.tag_config("ai_name",    foreground=MUTED,  font=("Helvetica", 9, "bold"))
    chat_text.tag_config("ai_msg",     foreground=TEXT,   lmargin1=8, lmargin2=8)
    chat_text.tag_config("sys_ok",     foreground=GREEN,  lmargin1=8, lmargin2=8,
                                        font=("Helvetica", 9))
    chat_text.tag_config("sys_warn",   foreground=YELLOW, lmargin1=8, lmargin2=8,
                                        font=("Helvetica", 9))
    chat_text.tag_config("sys_err",    foreground=RED,    lmargin1=8, lmargin2=8,
                                        font=("Helvetica", 9))
    chat_text.tag_config("divider",    foreground=BORDER)

    def _append_chat(role: str, text: str):
        def _do():
            chat_text.configure(state="normal")
            if role == "user":
                chat_text.insert("end", "あなた\n", "user_name")
                chat_text.insert("end", f"{text}\n\n", "user_msg")
            elif role == "assistant":
                chat_text.insert("end", "EditClone AI\n", "ai_name")
                chat_text.insert("end", f"{text}\n\n", "ai_msg")
            elif role == "system":
                icon = text[:1] if text[:1] in ("✓", "⚠", "✗") else "ℹ"
                tag  = {"✓": "sys_ok", "⚠": "sys_warn", "✗": "sys_err"}.get(icon, "sys_ok")
                chat_text.insert("end", f"{text}\n", tag)
            elif role == "divider":
                chat_text.insert("end", "─" * 50 + "\n", "divider")
            chat_text.configure(state="disabled")
            chat_text.see("end")
        root.after(0, _do)

    def _append_chat_sync(role: str, text: str):
        """バックグラウンドスレッドからも呼べるラッパー。"""
        _append_chat(role, text)

    # 初期メッセージ
    _append_chat("system", "✓ EditClone チャット準備完了")
    _append_chat("system", "ℹ AI編集タブで動画を処理するか、上のジョブ選択で過去の処理を選んでください")

    # チャット入力エリア
    input_frame = tk.Frame(tab_chat, bg=BG2)
    input_frame.pack(fill="x", side="bottom", padx=0, pady=0)

    chat_input = tk.Text(
        input_frame,
        height=3,
        bg=BG3,
        fg=TEXT,
        insertbackground=TEXT,
        relief="flat",
        font=("Helvetica", 11),
        wrap="word",
        borderwidth=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=PURPLE,
    )
    chat_input.pack(fill="x", padx=8, pady=(6, 2))

    btn_row = tk.Frame(input_frame, bg=BG2)
    btn_row.pack(fill="x", padx=8, pady=(2, 6))

    chat_status = tk.Label(btn_row, text="", bg=BG2, fg=MUTED, font=("Helvetica", 9))
    chat_status.pack(side="left", padx=(0, 8))

    def _set_cst(msg, fg=MUTED):
        chat_status.configure(text=msg, fg=fg)
        chat_status.update_idletasks()

    # FCPXML インポート用 (speed/transition/text などのPython非対応操作)
    _pending_ops_for_fcpxml: list = []

    def _do_fcpxml_import():
        ops = list(_pending_ops_for_fcpxml)
        job_id = _state.get("job_id", "")
        if not job_id or not ops:
            return
        btn_import_fcpxml.configure(state="disabled", text="インポート中...")
        _append_chat("system", "ℹ FCPXML を生成・インポート中...")

        def _run():
            import shutil
            try:
                # rich FCPXML をバックエンドから取得
                req = urllib.request.Request(
                    f"{_API_URL}/plugin/jobs/{job_id}/rich-fcpxml",
                    data=json.dumps({"operations": ops}).encode(),
                    method="POST",
                )
                _add_auth(req)
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=60) as r:
                    fcpxml_bytes = r.read()

                # 保存先ディレクトリを準備
                videos_dir = "Videos" if sys.platform == "win32" else "Movies"
                out_dir = Path.home() / videos_dir / "EditClone" / job_id
                out_dir.mkdir(parents=True, exist_ok=True)
                media_dir = out_dir / "media"
                media_dir.mkdir(parents=True, exist_ok=True)

                # ソースファイルパスを特定する（3段階フォールバック）
                src_file = ""

                # 1. state の source_clip（AI編集タブ経由）
                source_clip = _state.get("source_clip")
                if source_clip:
                    try:
                        props = source_clip.GetClipProperty() or {}
                        fp = props.get("File Path", "")
                        if fp and Path(fp).exists():
                            src_file = fp
                    except Exception:
                        pass

                # 2. DaVinci メディアプールで動画名を照合
                if not src_file and resolve:
                    try:
                        det = api_get(f"/plugin/jobs/{job_id}/details")
                        filename = det.get("filename", "")
                        for c in get_media_pool_clips(resolve):
                            try:
                                fp = (c.GetClipProperty() or {}).get("File Path", "")
                                if fp and Path(fp).name == filename and Path(fp).exists():
                                    src_file = fp
                                    _state["source_clip"] = c
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass

                # 3. ファイルダイアログで手動選択
                if not src_file:
                    _append_chat("system", "ℹ 元動画ファイルを選択してください...")
                    import tkinter.filedialog as fd
                    chosen = fd.askopenfilename(
                        title="元の動画ファイルを選択してください",
                        filetypes=[
                            ("動画ファイル", "*.mp4 *.mov *.avi *.mkv *.mxf *.m4v"),
                            ("すべてのファイル", "*.*"),
                        ],
                        parent=root,
                    )
                    if chosen:
                        src_file = chosen

                # メディアを media/ にコピーし、FCPXML パスを絶対 file:// URL に書き換える
                fcpxml_str = fcpxml_bytes.decode("utf-8")

                if src_file and Path(src_file).exists():
                    dest = media_dir / Path(src_file).name
                    if not dest.exists():
                        shutil.copy2(src_file, dest)
                        _append_chat("system", f"ℹ メディアをコピーしました: {Path(src_file).name}")
                    # ./media/xxx → file:///abs/path/media/xxx
                    media_dir_uri = media_dir.as_uri() + "/"
                    fcpxml_str = fcpxml_str.replace('"./media/', f'"{media_dir_uri}')
                    _append_chat("system", f"ℹ メディアパスを解決しました")
                else:
                    _append_chat("system", "⚠ 元動画が未選択 — タイムライン構造のみインポートします（メディアはオフライン状態）")

                # 書き換え済み FCPXML を保存
                fcpxml_path = out_dir / "rich_edit.fcpxml"
                fcpxml_path.write_text(fcpxml_str, encoding="utf-8")

                # DaVinci に FCPXML をインポート
                if resolve:
                    try:
                        project = resolve.GetProjectManager().GetCurrentProject()
                        media_pool = project.GetMediaPool()
                        tl = media_pool.ImportTimelineFromFile(str(fcpxml_path))
                        if tl:
                            project.SetCurrentTimeline(tl)
                            _append_chat("system", f"✓ FCPXMLインポート完了: 「{tl.GetName()}」")
                        else:
                            _append_chat("system",
                                f"⚠ 自動インポート失敗 — 手動でインポートしてください:\n{fcpxml_path}\n"
                                "DaVinci: ファイル → タイムラインをインポート")
                    except Exception as e:
                        _append_chat("system",
                            f"⚠ DaVinci API エラー: {e}\n"
                            f"手動インポート先: {fcpxml_path}")
                else:
                    _append_chat("system", f"ℹ FCPXML 保存完了: {fcpxml_path}")

            except Exception as e:
                _append_chat("system", f"✗ FCPXMLエラー: {e}")
            finally:
                root.after(0, lambda: btn_import_fcpxml.configure(
                    state="disabled", text="📥 FCPXMLインポート済み"
                ))

        threading.Thread(target=_run, daemon=True).start()

    def _send_implicit_feedback():
        """チャット編集後に暗黙的フィードバックを送信する（バックグラウンド）。"""
        try:
            job_id     = _state.get("job_id", "")
            project_id = _state.get("project_id", "")
            if not job_id:
                return
            # フィードバック送信はバックエンドの auto-accept ルートで十分なため
            # ここでは style profile の切り替え情報だけ送る
            if project_id:
                api_post(f"/projects/{project_id}/revisions", {
                    "notes": "auto:davinci_chat_edit",
                    "metadata": {"source": "davinci_plugin", "via": "chat_edit"},
                })
        except Exception:
            pass

    def _send_message(event=None):
        msg = chat_input.get("1.0", "end").strip()
        if not msg:
            return
        if not _state.get("job_id"):
            messagebox.showwarning("ジョブ未選択",
                                   "AI編集タブで動画を処理してください", parent=root)
            return
        chat_input.delete("1.0", "end")
        _append_chat("user", msg)
        _chat_history.append({"role": "user", "content": msg})
        _set_cst("AI が処理中...", MUTED)
        btn_send.configure(state="disabled")
        # FCPXML インポートボタンを隠す
        root.after(0, lambda: btn_import_fcpxml.pack_forget())

        def _worker():
            try:
                # 複数指示またはプロンプト長 > 20 文字の場合はエージェントチームを使用
                use_teams = len(msg) > 20 or "," in msg or "、" in msg
                payload = {
                    "prompt": msg,
                    "history": _chat_history[-10:],
                    "use_teams": use_teams,
                }
                if use_teams:
                    _set_cst("🤖 エージェントチーム起動中...", MUTED)
                resp = api_post(
                    f"/plugin/jobs/{_state['job_id']}/team-edit",
                    payload,
                    timeout=120,
                )
                ops              = resp.get("operations") or []
                fps              = float(resp.get("fps") or _state["fps"])
                duration         = float(resp.get("duration") or _state["duration"])
                srt_avail        = resp.get("srt_available", _state["srt_available"])
                needs_fcpxml     = resp.get("needs_fcpxml_import", False)
                agent_reports    = resp.get("agent_reports") or {}
                synthesis        = resp.get("synthesis") or ""
                agents_succeeded = resp.get("agents_succeeded") or []

                st_set("fps",           fps)
                st_set("duration",      duration)
                st_set("srt_available", srt_avail)

                # エージェントチームを使用した場合は各エージェントのレポートを表示
                if agent_reports:
                    agent_count = len(agents_succeeded)
                    _append_chat("system", f"ℹ {agent_count} エージェント協調完了")
                    label_map = {
                        "cut_agent":    "cut専門家",
                        "style_agent":  "style専門家",
                        "pacing_agent": "pacing専門家",
                        "hook_agent":   "hook専門家",
                    }
                    for agent_name, report in agent_reports.items():
                        if report and not report.startswith("("):
                            preview = report[:100].replace("\n", " ")
                            label = label_map.get(agent_name, agent_name)
                            _append_chat("system", f"🤖 [{label}] {preview}...")

                op_summary = synthesis if synthesis else "、".join(
                    op.get("description") or op.get("type", "?")
                    for op in ops
                ) or "操作なし"
                _append_chat("assistant", f"以下の編集を実行します:\n{op_summary}")
                _chat_history.append({"role": "assistant", "content": op_summary})

                _append_chat("divider", "")

                if not resolve:
                    _append_chat("system", "⚠ DaVinci 未接続 — 操作を適用できません")
                else:
                    apply_all_operations(
                        resolve, ops, _state,
                        _state.get("source_clip"),
                        _append_chat_sync,
                    )

                _append_chat("divider", "")

                # Python API 非対応の操作がある場合 → FCPXML インポートボタンを表示
                if needs_fcpxml and ops:
                    _pending_ops_for_fcpxml.clear()
                    _pending_ops_for_fcpxml.extend(ops)
                    _append_chat("system",
                        "ℹ 速度・トランジション等の操作は FCPXML 経由でインポートできます"
                    )
                    root.after(0, lambda: (
                        btn_import_fcpxml.configure(
                            state="normal", text="📥 FCPXML でインポート (速度/トランジション等)"
                        ),
                        btn_import_fcpxml.pack(fill="x", padx=8, pady=(0, 4), before=btn_send),
                    ))

                _set_cst("✓ 完了", GREEN)

                # 暗黙的フィードバック（バックグラウンド）
                threading.Thread(target=_send_implicit_feedback, daemon=True).start()

            except Exception as e:
                _append_chat("system", f"✗ エラー: {e}")
                _set_cst(f"エラー: {e}", RED)
            finally:
                root.after(0, lambda: btn_send.configure(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()
        return "break"

    def _on_enter(ev):
        if ev.state & 0x1:  # Shift+Enter → 改行
            return None
        _send_message()
        return "break"

    chat_input.bind("<Return>", _on_enter)

    btn_send = ttk.Button(btn_row, text="送信  ↵", style="P.TButton",
                          command=_send_message)
    btn_send.pack(side="right")

    tk.Label(btn_row, text="Shift+Enter で改行", bg=BG2, fg=BORDER,
             font=("Helvetica", 8)).pack(side="right", padx=(0, 10))

    # FCPXML インポートボタン（speed/transition 等の Python API 非対応操作用）
    # 必要な時だけ pack() で表示する
    btn_import_fcpxml = ttk.Button(
        input_frame, text="📥 FCPXML でインポート",
        style="B.TButton", command=_do_fcpxml_import,
    )
    # 初期状態では非表示

    # ================================================================
    # タブ3: 🎨 スタイル
    # ================================================================
    tab_styles = ttk.Frame(nb)
    nb.add(tab_styles, text="🎨 スタイル")

    sty_status = tk.Label(tab_styles, text="読み込み中...", bg=BG, fg=MUTED,
                          font=("Helvetica", 9))
    sty_status.pack(fill="x", padx=12, pady=(8, 4))

    sty_cols = ("act", "name", "noise", "silence")
    sty_tree = ttk.Treeview(tab_styles, columns=sty_cols, show="headings", height=10)
    sty_tree.heading("act",     text="")
    sty_tree.heading("name",    text="プロファイル名")
    sty_tree.heading("noise",   text="無音dB")
    sty_tree.heading("silence", text="最小秒")
    sty_tree.column("act",     width=22, stretch=False)
    sty_tree.column("name",    width=180, stretch=True)
    sty_tree.column("noise",   width=70,  stretch=False)
    sty_tree.column("silence", width=70,  stretch=False)
    sty_tree.pack(fill="both", expand=True, padx=10, pady=4)

    sty_btns = tk.Frame(tab_styles, bg=BG)
    sty_btns.pack(fill="x", padx=10, pady=(0, 8))

    def _activate_style():
        sel = sty_tree.selection()
        if not sel:
            return
        pid = sel[0]
        def _run():
            try:
                api_post(f"/plugin/style-profiles/{pid}/activate")
                sty_status.configure(text="✓ アクティブに設定しました", fg=GREEN)
                threading.Thread(target=_load_styles, daemon=True).start()
            except Exception as e:
                sty_status.configure(text=f"エラー: {e}", fg=RED)
        threading.Thread(target=_run, daemon=True).start()

    ttk.Button(sty_btns, text="✓ アクティブに設定", style="P.TButton",
               command=_activate_style).pack(side="left", padx=(0, 6))
    ttk.Button(sty_btns, text="↻ 更新",
               command=lambda: threading.Thread(target=_load_styles, daemon=True).start()
               ).pack(side="right")

    def _load_styles():
        try:
            resp = api_get("/plugin/style-profiles")
            styles_data.clear()
            styles_data.extend(resp.get("profiles", []))
            root.after(0, _render_styles)
            sty_status.configure(text=f"{len(styles_data)} 件")
        except Exception as e:
            sty_status.configure(text=f"取得エラー: {e}", fg=RED)

    def _render_styles():
        sty_tree.delete(*sty_tree.get_children())
        vals = ["なし（デフォルト）"]
        for p in styles_data:
            sty_tree.insert("", "end", iid=p["id"],
                            values=("★" if p.get("is_active") else "", p["name"],
                                    p.get("noise_db", -30),
                                    p.get("min_silence_seconds", 0.5)))
            vals.append(p["name"])
        style_combo["values"] = vals
        if style_combo.current() < 0:
            style_combo.current(0)

    # ================================================================
    # タブ4: ⚙️ 設定
    # ================================================================
    tab_settings = ttk.Frame(nb)
    nb.add(tab_settings, text="⚙️ 設定")

    tk.Label(tab_settings, text="EditClone API URL:", bg=BG, fg=MUTED,
             font=("Helvetica", 10)).pack(anchor="w", padx=12, pady=(16, 2))
    url_var = tk.StringVar(value=_API_URL or _DEFAULT_API_URL)
    ttk.Entry(tab_settings, textvariable=url_var,
              font=("Helvetica", 10)).pack(fill="x", padx=12, pady=(0, 10))

    tk.Label(tab_settings,
             text="API トークン (eck_...)  ※ Dashboard → Account → API Keys で取得",
             bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(anchor="w", padx=12, pady=(0, 2))
    token_var = tk.StringVar(value=_API_TOKEN)
    ttk.Entry(tab_settings, textvariable=token_var, show="•",
              font=("Helvetica", 10)).pack(fill="x", padx=12, pady=(0, 10))

    set_status = tk.Label(tab_settings, text="", bg=BG, fg=MUTED, font=("Helvetica", 9))
    set_status.pack(fill="x", padx=12, pady=(0, 6))

    def _save_settings():
        global _API_URL, _API_TOKEN
        url   = url_var.get().strip().rstrip("/")
        token = token_var.get().strip()
        if not url or not token:
            set_status.configure(text="URL と Token を両方入力してください", fg=RED)
            return
        _API_URL = url
        _API_TOKEN = token
        _save_config(url, token)
        set_status.configure(text="✓ 保存しました", fg=GREEN)
        threading.Thread(target=lambda: (_load_jobs(), _load_styles()), daemon=True).start()

    def _test_conn():
        url = url_var.get().strip().rstrip("/")
        set_status.configure(text="接続テスト中...", fg=MUTED)
        def _run():
            try:
                req = urllib.request.Request(f"{url}/health")
                with urllib.request.urlopen(req, timeout=5) as r:
                    ver = json.loads(r.read()).get("version", "?")
                set_status.configure(text=f"✓ 接続成功 (v{ver})", fg=GREEN)
            except Exception as e:
                set_status.configure(text=f"接続失敗: {e}", fg=RED)
        threading.Thread(target=_run, daemon=True).start()

    def _show_diag():
        lines = [
            f"DaVinci: {'✓ 接続済み' if resolve else '✗ 未接続'}",
            f"Python:  {sys.executable}",
            f"版数:    {sys.version.split()[0]}",
            "",
        ] + (_RESOLVE_ERRORS or ["(ログなし)"])
        messagebox.showinfo("診断", "\n".join(lines), parent=root)

    btns = tk.Frame(tab_settings, bg=BG)
    btns.pack(fill="x", padx=12, pady=6)
    ttk.Button(btns, text="保存", style="P.TButton",
               command=_save_settings).pack(side="left", padx=(0, 6))
    ttk.Button(btns, text="接続テスト",
               command=_test_conn).pack(side="left", padx=(0, 6))
    ttk.Button(btns, text="DaVinci 診断",
               command=_show_diag).pack(side="left")

    tk.Label(tab_settings,
             text="トークン取得: EditClone Web → アカウント → APIキーを生成",
             bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(anchor="w", padx=12, pady=(16, 4))
    tk.Label(tab_settings, text=f"設定ファイル: {_CONFIG_PATH}",
             bg=BG, fg=BORDER, font=("Helvetica", 8)).pack(anchor="w", padx=12)

    # ================================================================
    # 共有ロード関数
    # ================================================================

    def _load_jobs():
        try:
            resp = api_get("/plugin/jobs")
            jobs_data.clear()
            jobs_data.extend(resp.get("jobs", []))
            root.after(0, _update_job_selector)
        except Exception:
            pass

    def _update_job_selector():
        if not jobs_data:
            return
        def _fmt(j):
            name = j.get("video_name", "不明")
            date = (j.get("created_at") or "")[:10]
            dur  = float(j.get("duration", 0))
            dur_str = f"{int(dur//60)}:{int(dur%60):02d}" if dur > 0 else "?"
            return f"{name}  [{dur_str}]  {date}"
        vals = ["─ ジョブを選択 ─"] + [_fmt(j) for j in jobs_data]
        job_sel_cb["values"] = vals
        # 現在の job_id を選択
        cur = _state.get("job_id", "")
        if cur:
            for i, j in enumerate(jobs_data):
                if j["job_id"] == cur:
                    job_sel_cb.current(i + 1)
                    break
        elif jobs_data:
            job_sel_cb.current(0)

    # ================================================================
    # 初期ロード
    # ================================================================

    def _initial_load():
        time.sleep(0.3)
        if _API_URL and _API_TOKEN:
            _load_jobs()
            _load_styles()
        else:
            root.after(0, lambda: nb.select(tab_settings))
        if resolve:
            root.after(0, _reload_clips)

    threading.Thread(target=_initial_load, daemon=True).start()
    root.mainloop()


# ================================================================
# エントリーポイント
# ================================================================

def main():
    global _API_URL, _API_TOKEN
    _API_URL, _API_TOKEN = _load_config()

    if not _API_URL or not _API_TOKEN:
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            url   = simpledialog.askstring("EditClone 設定",
                                           "EditClone API URL:",
                                           initialvalue=_DEFAULT_API_URL,
                                           parent=root)
            token = simpledialog.askstring("EditClone 設定",
                                           "API トークン (eck_...)\nダッシュボード → Account → API Keys で取得",
                                           parent=root)
            root.destroy()
            if url and token:
                _API_URL   = url.strip().rstrip("/")
                _API_TOKEN = token.strip()
                _save_config(_API_URL, _API_TOKEN)
        except Exception:
            print("[EditClone] 設定ファイルが必要です:", _CONFIG_PATH)
            return

    run_gui()


if __name__ == "__main__":
    main()
