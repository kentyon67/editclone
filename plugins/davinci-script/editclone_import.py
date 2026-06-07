#!/usr/bin/env python3
"""
EditClone — DaVinci Resolve AI 編集エージェント
=================================================
DaVinci Resolve の Scripts メニューから実行すると起動する
マルチタブ GUI エージェントです。

タブ機能:
  ジョブ   — 完了済みジョブ一覧・インポート
  AI編集   — 自然言語で再編集指示・自動インポート
  スタイル — Style Profile 管理・切り替え
  設定     — API URL / トークン

インストール方法:
  macOS:   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
  Windows: %APPDATA%\\Blackmagic Design\\DaVinci Resolve\\Support\\Fusion\\Scripts\\Utility\\
  Linux:   ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# ================================================================
# 設定管理
# ================================================================

_CONFIG_PATH = Path.home() / ".editclone" / "config.json"
_API_URL = ""
_API_TOKEN = ""


def _load_config() -> tuple[str, str]:
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("api_url", ""), data.get("api_token", "")
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

def _add_auth_header(req: urllib.request.Request) -> None:
    """eck_ プレフィックスの API キーは X-Api-Key、それ以外は Bearer で送信。"""
    if not _API_TOKEN:
        return
    if _API_TOKEN.startswith("eck_"):
        req.add_header("X-Api-Key", _API_TOKEN)
    else:
        req.add_header("Authorization", f"Bearer {_API_TOKEN}")


def api_request(method: str, endpoint: str, payload: dict | None = None, timeout: int = 30) -> dict:
    url = f"{_API_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    _add_auth_header(req)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def api_get(endpoint: str, timeout: int = 30) -> dict:
    return api_request("GET", endpoint, timeout=timeout)


def api_post(endpoint: str, payload: dict | None = None, timeout: int = 30) -> dict:
    return api_request("POST", endpoint, payload, timeout=timeout)


def download_bytes(url_path: str, timeout: int = 120) -> bytes:
    url = f"{_API_URL}{url_path}"
    req = urllib.request.Request(url)
    _add_auth_header(req)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ================================================================
# DaVinci Resolve API
# ================================================================

def get_resolve():
    try:
        import DaVinciResolveScript as dvr_script
        return dvr_script.scriptapp("Resolve")
    except ImportError:
        pass
    for path in [
        "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/",
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\\",
        "/opt/resolve/libs/Fusion/",
    ]:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    try:
        import DaVinciResolveScript as dvr_script
        return dvr_script.scriptapp("Resolve")
    except ImportError:
        return None


def import_to_resolve(resolve, files: dict) -> str:
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if not project:
        return "No active project"

    media_pool = project.GetMediaPool()
    root_bin = media_pool.GetRootFolder()

    editclone_bin = None
    for subfolder in root_bin.GetSubFolderList():
        if subfolder.GetName() == "EditClone":
            editclone_bin = subfolder
            break
    if editclone_bin is None:
        editclone_bin = media_pool.AddSubFolder(root_bin, "EditClone")

    media_pool.SetCurrentFolder(editclone_bin)

    if files.get("media"):
        clips = media_pool.ImportMedia(files["media"])
        if clips:
            print(f"Imported {len(clips)} media file(s)")

    if files.get("srt"):
        try:
            media_pool.ImportMedia([files["srt"]])
        except Exception:
            pass

    if files.get("fcpxml"):
        timelines = media_pool.ImportTimelineFromFile(files["fcpxml"])
        if timelines:
            project.SetCurrentTimeline(timelines[0])
            return "ok"
        if files.get("media"):
            tl = media_pool.CreateTimelineFromClips("EditClone", [])
            return "ok_no_xml" if tl else "timeline_import_failed"
        return "timeline_import_failed"

    return "ok_media_only"


def _download_and_extract(job_id: str) -> dict:
    """ZIP をダウンロードして永続パスに展開し、ファイルパス dict を返す。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_data = download_bytes(f"/jobs/{job_id}/download")
        zip_path = tmpdir_path / f"{job_id}.zip"
        zip_path.write_bytes(zip_data)

        extract_dir = tmpdir_path / "ex"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)

        files: dict = {"fcpxml": None, "media": [], "srt": None}
        for f in extract_dir.rglob("*"):
            if f.suffix == ".fcpxml":
                files["fcpxml"] = str(f)
            elif f.suffix in {".mp4", ".mov", ".m4v", ".mxf"}:
                files["media"].append(str(f))
            elif f.suffix == ".srt":
                files["srt"] = str(f)

        # 永続ディレクトリにコピー
        persist_dir = Path.home() / "Movies" / "EditClone" / job_id
        persist_dir.mkdir(parents=True, exist_ok=True)

        if files["fcpxml"]:
            dest = persist_dir / Path(files["fcpxml"]).name
            shutil.copy2(files["fcpxml"], dest)
            files["fcpxml"] = str(dest)
        new_media = []
        for m in files["media"]:
            dest = persist_dir / Path(m).name
            shutil.copy2(m, dest)
            new_media.append(str(dest))
        files["media"] = new_media
        if files["srt"]:
            dest = persist_dir / Path(files["srt"]).name
            shutil.copy2(files["srt"], dest)
            files["srt"] = str(dest)

        return files


# ================================================================
# GUI — tkinter + ttk.Notebook 多タブエージェント
# ================================================================

def run_gui():
    global _API_URL, _API_TOKEN

    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, scrolledtext
    except ImportError:
        print("[EditClone] tkinter が利用できません。コンソールモードを使用してください。")
        run_console()
        return

    resolve = get_resolve()

    # ---------- カラー定義 ----------
    BG = "#0f0f14"
    BG2 = "#1a1a24"
    BG3 = "#22222e"
    BORDER = "#2e2e3e"
    PURPLE = "#a855f7"
    TEXT = "#e8e8f0"
    MUTED = "#8888a8"
    GREEN = "#22c55e"
    RED = "#ef4444"

    root = tk.Tk()
    root.title("EditClone Agent — DaVinci Resolve")
    root.configure(bg=BG)
    root.geometry("440x620")
    root.resizable(True, True)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=("Helvetica", 11))
    style.configure("TNotebook", background=BG2, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG3, foreground=MUTED,
                    padding=[12, 6], borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", PURPLE)])
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("TEntry", fieldbackground=BG2, foreground=TEXT, borderwidth=1)
    style.configure("TButton", background=BG3, foreground=TEXT, borderwidth=0, padding=[8, 4])
    style.map("TButton", background=[("active", BG2)], foreground=[("active", PURPLE)])
    style.configure("Primary.TButton", background=PURPLE, foreground="#ffffff")
    style.map("Primary.TButton", background=[("active", "#7c3aed")])
    style.configure("Import.TButton", background="#2563eb", foreground="#ffffff")
    style.map("Import.TButton", background=[("active", "#1d4ed8")])
    style.configure("TProgressbar", troughcolor=BG3, background=PURPLE, borderwidth=0, thickness=6)
    style.configure("Treeview", background=BG2, foreground=TEXT, fieldbackground=BG2,
                    rowheight=28, borderwidth=0)
    style.map("Treeview", background=[("selected", BG3)], foreground=[("selected", PURPLE)])
    style.configure("Treeview.Heading", background=BG3, foreground=MUTED, borderwidth=0)

    # ---------- ヘッダー ----------
    header = tk.Frame(root, bg=BG2, height=44)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)
    tk.Label(header, text="✦ EditClone Agent", bg=BG2, fg=PURPLE,
             font=("Helvetica", 13, "bold")).pack(side="left", padx=14, pady=10)
    resolve_label = tk.Label(
        header,
        text="✓ DaVinci 接続済み" if resolve else "✗ DaVinci 未接続",
        bg=BG2,
        fg=GREEN if resolve else RED,
        font=("Helvetica", 9),
    )
    resolve_label.pack(side="right", padx=14)

    # ---------- ノートブック ----------
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=0, pady=0)

    # ==============================
    # タブ共通ヘルパー
    # ==============================

    jobs_data: list[dict] = []
    styles_data: list[dict] = []

    def status_bar(parent, text="", fg=MUTED) -> tk.Label:
        lbl = tk.Label(parent, text=text, bg=BG, fg=fg, font=("Helvetica", 9),
                       wraplength=400, justify="left")
        lbl.pack(fill="x", padx=10, pady=(0, 6))
        return lbl

    def set_status(lbl: tk.Label, text: str, fg: str = MUTED):
        lbl.configure(text=text, fg=fg)
        lbl.update_idletasks()

    # ==============================
    # ジョブ タブ
    # ==============================

    tab_jobs = ttk.Frame(nb)
    nb.add(tab_jobs, text="📁 ジョブ")

    jobs_status = status_bar(tab_jobs, "読み込み中...")

    jobs_tree_frame = tk.Frame(tab_jobs, bg=BG)
    jobs_tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

    jobs_cols = ("name", "date", "cuts")
    jobs_tree = ttk.Treeview(jobs_tree_frame, columns=jobs_cols, show="headings",
                              height=10, selectmode="browse")
    jobs_tree.heading("name", text="動画名")
    jobs_tree.heading("date", text="日付")
    jobs_tree.heading("cuts", text="カット")
    jobs_tree.column("name", width=200, stretch=True)
    jobs_tree.column("date", width=90, stretch=False)
    jobs_tree.column("cuts", width=50, stretch=False)
    jobs_tree.pack(fill="both", expand=True)

    jobs_scroll = ttk.Scrollbar(jobs_tree_frame, orient="vertical", command=jobs_tree.yview)
    jobs_scroll.pack(side="right", fill="y")
    jobs_tree.configure(yscrollcommand=jobs_scroll.set)

    # 選択ジョブ詳細パネル
    detail_frame = tk.LabelFrame(tab_jobs, text="選択中のジョブ", bg=BG, fg=MUTED,
                                 font=("Helvetica", 9), pady=4)
    detail_frame.pack(fill="x", padx=10, pady=4)
    detail_label = tk.Label(detail_frame, text="ジョブをクリックして選択", bg=BG, fg=MUTED,
                            font=("Helvetica", 10))
    detail_label.pack(padx=8, pady=2)

    btns_frame = tk.Frame(tab_jobs, bg=BG)
    btns_frame.pack(fill="x", padx=10, pady=(0, 8))

    def _import_selected():
        sel = jobs_tree.selection()
        if not sel:
            messagebox.showwarning("選択なし", "インポートするジョブを選択してください", parent=root)
            return
        job_id = sel[0]  # iid = job_id
        _do_import(job_id)

    def _redit_selected():
        sel = jobs_tree.selection()
        if not sel:
            messagebox.showwarning("選択なし", "再編集するジョブを選択してください", parent=root)
            return
        job_id = sel[0]  # iid = job_id
        nb.select(tab_agent)
        agent_job_var.set(job_id)
        _refresh_agent_combo()

    def _do_import(job_id: str, after_edit: bool = False):
        set_status(jobs_status, "ダウンロード中...", MUTED)
        btn_import.configure(state="disabled")

        def _run():
            try:
                files = _download_and_extract(job_id)
                if not resolve:
                    set_status(jobs_status, "DaVinci Resolve に接続できません", RED)
                    return
                result = import_to_resolve(resolve, files)
                if result.startswith("ok"):
                    msg = f"✓ インポート完了！" + (" (AI再編集)" if after_edit else "")
                    set_status(jobs_status, msg, GREEN)
                else:
                    set_status(jobs_status, f"インポート結果: {result}", RED)
            except Exception as e:
                set_status(jobs_status, f"エラー: {e}", RED)
            finally:
                btn_import.configure(state="normal")

        threading.Thread(target=_run, daemon=True).start()

    btn_import = ttk.Button(btns_frame, text="📥 DaVinci にインポート",
                            style="Import.TButton", command=_import_selected)
    btn_import.pack(side="left", padx=(0, 6))

    ttk.Button(btns_frame, text="🤖 AI再編集",
               command=_redit_selected).pack(side="left", padx=(0, 6))

    ttk.Button(btns_frame, text="↻ 更新",
               command=lambda: threading.Thread(target=_load_jobs, daemon=True).start()
               ).pack(side="right")

    def _load_jobs():
        set_status(jobs_status, "読み込み中...", MUTED)
        try:
            resp = api_get("/plugin/jobs")
            jobs_data.clear()
            jobs_data.extend(resp.get("jobs", []))
            _render_jobs()
            set_status(jobs_status, f"{len(jobs_data)} 件のジョブ", MUTED)
        except Exception as e:
            set_status(jobs_status, f"取得エラー: {e}", RED)

    def _render_jobs():
        jobs_tree.delete(*jobs_tree.get_children())
        for job in jobs_data:
            date_str = (job.get("created_at") or "")[:10]
            cut_str = str(job.get("cut_count", ""))
            jobs_tree.insert("", "end", iid=job["job_id"],
                             values=(job["video_name"], date_str, cut_str))

    def _on_job_select(event):
        sel = jobs_tree.selection()
        if not sel:
            return
        job_id = sel[0]  # iid = job_id
        job = next((j for j in jobs_data if j["job_id"] == job_id), None)
        if job:
            detail_label.configure(
                text=f"{job['video_name']}\n"
                     f"カット数: {job.get('cut_count', '?')} 件"
                     + (f"\n指示: 「{job['prompt'][:40]}」" if job.get("prompt") else ""),
                fg=TEXT,
            )

    jobs_tree.bind("<<TreeviewSelect>>", _on_job_select)

    # ==============================
    # AI編集 タブ
    # ==============================

    tab_agent = ttk.Frame(nb)
    nb.add(tab_agent, text="🤖 AI編集")

    tk.Label(tab_agent, text="対象ジョブ:", bg=BG, fg=MUTED,
             font=("Helvetica", 10)).pack(anchor="w", padx=12, pady=(12, 2))

    agent_job_var = tk.StringVar(value="")
    agent_combo = ttk.Combobox(tab_agent, textvariable=agent_job_var, state="readonly",
                                font=("Helvetica", 10))
    agent_combo.pack(fill="x", padx=12, pady=(0, 8))

    def _refresh_agent_combo():
        names = [f"{j['video_name']} ({(j.get('created_at') or '')[:10]})"
                 for j in jobs_data]
        agent_combo["values"] = names
        ids = [j["job_id"] for j in jobs_data]
        agent_combo._ids = ids

        # agent_job_var が job_id なら対応 index を選択
        cur = agent_job_var.get()
        if cur and cur in ids:
            agent_combo.current(ids.index(cur))
        elif names:
            agent_combo.current(0)

    tk.Label(tab_agent, text="編集指示:", bg=BG, fg=MUTED,
             font=("Helvetica", 10)).pack(anchor="w", padx=12, pady=(0, 2))

    agent_text = tk.Text(tab_agent, height=4, bg=BG2, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=("Helvetica", 11), wrap="word",
                         borderwidth=1, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=PURPLE)
    agent_text.pack(fill="x", padx=12, pady=(0, 6))
    agent_text.insert("1.0", "例: 冒頭の挨拶をカットして、フィラーワードも除去してください")
    agent_text.configure(fg=MUTED)

    def _on_text_focus_in(e):
        if agent_text.cget("fg") == MUTED:
            agent_text.delete("1.0", "end")
            agent_text.configure(fg=TEXT)

    def _on_text_focus_out(e):
        if not agent_text.get("1.0", "end").strip():
            agent_text.insert("1.0", "例: 冒頭の挨拶をカットして、フィラーワードも除去してください")
            agent_text.configure(fg=MUTED)

    agent_text.bind("<FocusIn>", _on_text_focus_in)
    agent_text.bind("<FocusOut>", _on_text_focus_out)

    # クイックプロンプトボタン
    quick_frame = tk.Frame(tab_agent, bg=BG)
    quick_frame.pack(fill="x", padx=12, pady=(0, 8))
    tk.Label(quick_frame, text="クイック:", bg=BG, fg=MUTED, font=("Helvetica", 9)).pack(side="left")

    quick_prompts = [
        ("冒頭カット", "冒頭の挨拶・タイトルコールをカット"),
        ("フィラー除去", "えー、あの、まあ などのフィラーワードをすべてカット"),
        ("告知カット", "チャンネル登録・いいね・SNS告知のセグメントをカット"),
        ("テンポ強化", "テンポよく：沈黙・間延びを積極的にカットしてテンポアップ"),
    ]

    for label, prompt in quick_prompts:
        btn = tk.Button(quick_frame, text=label, bg=BG3, fg=MUTED, relief="flat",
                        font=("Helvetica", 9), cursor="hand2",
                        padx=6, pady=2,
                        command=lambda p=prompt: (
                            agent_text.configure(fg=TEXT),
                            agent_text.delete("1.0", "end"),
                            agent_text.insert("1.0", p),
                        ))
        btn.pack(side="left", padx=2)

    agent_status = status_bar(tab_agent, "")

    agent_progress = ttk.Progressbar(tab_agent, mode="indeterminate", style="TProgressbar")
    agent_progress.pack(fill="x", padx=12, pady=(0, 8))

    def _start_agent_edit():
        # ジョブ選択チェック
        idx = agent_combo.current()
        if idx < 0 or idx >= len(jobs_data):
            messagebox.showwarning("選択なし", "対象ジョブを選択してください", parent=root)
            return
        job_id = jobs_data[idx]["job_id"]

        prompt = agent_text.get("1.0", "end").strip()
        if not prompt or prompt.startswith("例:"):
            messagebox.showwarning("入力なし", "編集指示を入力してください", parent=root)
            return

        btn_agent_send.configure(state="disabled", text="処理中...")
        agent_progress.start(10)
        set_status(agent_status, "AI 編集リクエストを送信中...", MUTED)

        def _run():
            try:
                resp = api_post(f"/plugin/jobs/{job_id}/agent-edit", {"prompt": prompt})
                new_job_id = resp.get("job_id")
                if not new_job_id:
                    raise ValueError("ジョブIDが取得できませんでした")
                set_status(agent_status, "処理中... (完了まで1〜3分かかります)", MUTED)
                _poll_agent_job(job_id=new_job_id, original_job_id=job_id)
            except Exception as e:
                agent_progress.stop()
                btn_agent_send.configure(state="normal", text="🤖 AI編集を開始")
                set_status(agent_status, f"エラー: {e}", RED)

        threading.Thread(target=_run, daemon=True).start()

    def _poll_agent_job(job_id: str, original_job_id: str):
        max_attempts = 120
        for attempt in range(max_attempts):
            time.sleep(3)
            try:
                resp = api_get(f"/plugin/jobs/{job_id}/poll")
                status = resp.get("status", "")
                progress = resp.get("progress", "")
                if progress:
                    set_status(agent_status, f"処理中: {progress}", MUTED)

                if status == "completed":
                    agent_progress.stop()
                    btn_agent_send.configure(state="normal", text="🤖 AI編集を開始")
                    set_status(agent_status, "✓ 編集完了！DaVinci にインポートします...", GREEN)
                    _do_import(job_id, after_edit=True)
                    threading.Thread(target=_load_jobs, daemon=True).start()
                    return
                elif status == "failed":
                    raise ValueError(resp.get("error") or "処理に失敗しました")
            except StopIteration:
                break
            except Exception as e:
                agent_progress.stop()
                btn_agent_send.configure(state="normal", text="🤖 AI編集を開始")
                set_status(agent_status, f"エラー: {e}", RED)
                return

        agent_progress.stop()
        btn_agent_send.configure(state="normal", text="🤖 AI編集を開始")
        set_status(agent_status, "タイムアウト: Web で状態を確認してください", RED)

    btn_agent_send = ttk.Button(tab_agent, text="🤖 AI編集を開始",
                                style="Primary.TButton", command=_start_agent_edit)
    btn_agent_send.pack(fill="x", padx=12, pady=(0, 4))

    ttk.Button(tab_agent, text="↻ ジョブ一覧を更新",
               command=lambda: threading.Thread(target=lambda: (
                   _load_jobs(), _refresh_agent_combo()
               ), daemon=True).start()
               ).pack(fill="x", padx=12, pady=(0, 12))

    # ==============================
    # スタイル タブ
    # ==============================

    tab_styles = ttk.Frame(nb)
    nb.add(tab_styles, text="🎨 スタイル")

    styles_status = status_bar(tab_styles, "読み込み中...")

    styles_tree_frame = tk.Frame(tab_styles, bg=BG)
    styles_tree_frame.pack(fill="both", expand=True, padx=10, pady=4)

    styles_cols = ("status", "name", "noise", "silence")
    styles_tree = ttk.Treeview(styles_tree_frame, columns=styles_cols, show="headings", height=8)
    styles_tree.heading("status", text="")
    styles_tree.heading("name", text="プロファイル名")
    styles_tree.heading("noise", text="無音dB")
    styles_tree.heading("silence", text="最小秒")
    styles_tree.column("status", width=22, stretch=False)
    styles_tree.column("name", width=160, stretch=True)
    styles_tree.column("noise", width=70, stretch=False)
    styles_tree.column("silence", width=70, stretch=False)
    styles_tree.pack(fill="both", expand=True)

    styles_scroll = ttk.Scrollbar(styles_tree_frame, orient="vertical", command=styles_tree.yview)
    styles_scroll.pack(side="right", fill="y")
    styles_tree.configure(yscrollcommand=styles_scroll.set)

    styles_detail = tk.Label(tab_styles, text="", bg=BG, fg=MUTED,
                             font=("Helvetica", 9), wraplength=400, justify="left")
    styles_detail.pack(fill="x", padx=10, pady=2)

    styles_btns = tk.Frame(tab_styles, bg=BG)
    styles_btns.pack(fill="x", padx=10, pady=(4, 8))

    def _activate_selected_style():
        sel = styles_tree.selection()
        if not sel:
            messagebox.showwarning("選択なし", "スタイルを選択してください", parent=root)
            return
        profile_id = sel[0]  # iid = profile_id

        def _run():
            try:
                api_post(f"/plugin/style-profiles/{profile_id}/activate")
                set_status(styles_status, "✓ スタイルを変更しました", GREEN)
                threading.Thread(target=_load_styles, daemon=True).start()
            except Exception as e:
                set_status(styles_status, f"エラー: {e}", RED)

        threading.Thread(target=_run, daemon=True).start()

    def _on_style_select(event):
        sel = styles_tree.selection()
        if not sel:
            return
        profile_id = sel[0]  # iid = profile_id
        profile = next((p for p in styles_data if p["id"] == profile_id), None)
        if profile:
            prompt = (profile.get("default_prompt") or "")[:60]
            styles_detail.configure(
                text=f"プロンプト: 「{prompt}{'...' if len(profile.get('default_prompt') or '') > 60 else ''}」"
                if prompt else "プロンプト未設定",
                fg=TEXT,
            )

    styles_tree.bind("<<TreeviewSelect>>", _on_style_select)

    ttk.Button(styles_btns, text="✓ アクティブに設定",
               style="Primary.TButton", command=_activate_selected_style).pack(side="left", padx=(0, 6))
    ttk.Button(styles_btns, text="↻ 更新",
               command=lambda: threading.Thread(target=_load_styles, daemon=True).start()
               ).pack(side="right")

    def _load_styles():
        set_status(styles_status, "読み込み中...", MUTED)
        try:
            resp = api_get("/plugin/style-profiles")
            styles_data.clear()
            styles_data.extend(resp.get("profiles", []))
            _render_styles()
            set_status(styles_status, f"{len(styles_data)} 件のプロファイル", MUTED)
        except Exception as e:
            set_status(styles_status, f"取得エラー: {e}", RED)

    def _render_styles():
        styles_tree.delete(*styles_tree.get_children())
        for p in styles_data:
            active = "★" if p.get("is_active") else ""
            noise = str(p.get("noise_db", -30))
            silence = str(p.get("min_silence_seconds", 0.5))
            styles_tree.insert("", "end", iid=p["id"],
                               values=(active, p["name"], noise, silence))

    # ==============================
    # 設定 タブ
    # ==============================

    tab_settings = ttk.Frame(nb)
    nb.add(tab_settings, text="⚙️ 設定")

    tk.Label(tab_settings, text="EditClone API URL:", bg=BG, fg=MUTED,
             font=("Helvetica", 10)).pack(anchor="w", padx=12, pady=(16, 2))
    url_var = tk.StringVar(value=_API_URL)
    url_entry = ttk.Entry(tab_settings, textvariable=url_var, font=("Helvetica", 10))
    url_entry.pack(fill="x", padx=12, pady=(0, 10))

    tk.Label(tab_settings, text="API トークン:", bg=BG, fg=MUTED,
             font=("Helvetica", 10)).pack(anchor="w", padx=12, pady=(0, 2))
    token_var = tk.StringVar(value=_API_TOKEN)
    token_entry = ttk.Entry(tab_settings, textvariable=token_var, show="•",
                             font=("Helvetica", 10))
    token_entry.pack(fill="x", padx=12, pady=(0, 10))

    settings_status = status_bar(tab_settings, "")

    def _save_settings():
        global _API_URL, _API_TOKEN
        url = url_var.get().strip().rstrip("/")
        token = token_var.get().strip()
        if not url or not token:
            set_status(settings_status, "URL と Token を両方入力してください", RED)
            return
        _API_URL = url
        _API_TOKEN = token
        _save_config(url, token)
        set_status(settings_status, "✓ 設定を保存しました", GREEN)
        # 保存後にデータをリロード
        threading.Thread(target=lambda: (_load_jobs(), _load_styles()), daemon=True).start()

    def _test_connection():
        url = url_var.get().strip().rstrip("/")
        token = token_var.get().strip()
        if not url:
            set_status(settings_status, "URL を入力してください", RED)
            return
        set_status(settings_status, "接続テスト中...", MUTED)

        def _run():
            try:
                req = urllib.request.Request(f"{url}/health")
                with urllib.request.urlopen(req, timeout=5) as r:
                    data = json.loads(r.read())
                ver = data.get("version", "?")
                set_status(settings_status, f"✓ 接続成功 (v{ver})", GREEN)
            except Exception as e:
                set_status(settings_status, f"接続失敗: {e}", RED)

        threading.Thread(target=_run, daemon=True).start()

    btns_s = tk.Frame(tab_settings, bg=BG)
    btns_s.pack(fill="x", padx=12, pady=4)
    ttk.Button(btns_s, text="保存", style="Primary.TButton",
               command=_save_settings).pack(side="left", padx=(0, 6))
    ttk.Button(btns_s, text="接続テスト",
               command=_test_connection).pack(side="left")

    tk.Label(tab_settings,
             text="トークンの取得:\nEditClone ウェブアプリ → アカウント → Plugin Token",
             bg=BG, fg=MUTED, font=("Helvetica", 9), justify="left").pack(
        anchor="w", padx=12, pady=(16, 4))

    tk.Label(tab_settings,
             text=f"設定ファイル: {_CONFIG_PATH}",
             bg=BG, fg=BORDER, font=("Helvetica", 8)).pack(anchor="w", padx=12)

    # ==============================
    # 初期データ読み込み
    # ==============================

    def _initial_load():
        time.sleep(0.3)
        if _API_URL and _API_TOKEN:
            _load_jobs()
            _load_styles()
            root.after(0, _refresh_agent_combo)
        else:
            set_status(jobs_status, "設定タブで API URL と Token を入力してください", RED)
            nb.select(tab_settings)

    threading.Thread(target=_initial_load, daemon=True).start()

    root.mainloop()


# ================================================================
# コンソールフォールバック（tkinter 利用不可時）
# ================================================================

def run_console():
    global _API_URL, _API_TOKEN
    print("EditClone Import (Console Mode)")

    resolve = get_resolve()
    if not resolve:
        print("[ERROR] DaVinci Resolve に接続できません")
        return

    try:
        jobs_resp = api_get("/plugin/jobs")
        jobs = jobs_resp.get("jobs", [])
    except Exception as e:
        print(f"[ERROR] API エラー: {e}")
        return

    if not jobs:
        print("完了済みジョブがありません")
        return

    print("\n=== 完了済みジョブ ===")
    for i, j in enumerate(jobs[:10]):
        print(f"  [{i+1}] {j['video_name']} — {(j.get('created_at') or '')[:10]}")

    choice = input("\nインポートするジョブ番号 [1]: ").strip()
    idx = int(choice) - 1 if choice else 0
    if idx < 0 or idx >= len(jobs):
        idx = 0

    job = jobs[idx]
    print(f"選択: {job['video_name']}")

    files = _download_and_extract(job["job_id"])
    result = import_to_resolve(resolve, files)
    print(f"インポート結果: {result}")


# ================================================================
# エントリーポイント
# ================================================================

def main():
    global _API_URL, _API_TOKEN
    _API_URL, _API_TOKEN = _load_config()

    if not _API_URL or not _API_TOKEN:
        # GUI で初期設定
        try:
            import tkinter as tk
            from tkinter import simpledialog
            root = tk.Tk()
            root.withdraw()
            url = simpledialog.askstring(
                "EditClone 設定",
                "EditClone API URL:\n例: https://your-app.railway.app",
                parent=root,
            )
            token = simpledialog.askstring(
                "EditClone 設定",
                "Plugin トークンを貼り付けてください",
                parent=root,
            )
            root.destroy()
            if url and token:
                _API_URL = url.strip().rstrip("/")
                _API_TOKEN = token.strip()
                _save_config(_API_URL, _API_TOKEN)
        except Exception:
            print("[EditClone] 設定ファイルが必要です:", _CONFIG_PATH)
            return

    run_gui()


if __name__ == "__main__":
    main()
