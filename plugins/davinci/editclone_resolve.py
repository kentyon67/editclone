#!/usr/bin/env python3
"""
EditClone — DaVinci Resolve 連携スクリプト（GUI付き）
======================================================

インストール方法:
  1. このファイルを以下のフォルダにコピーしてください:
     - macOS: ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
     - Windows: C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Fusion\\Scripts\\Utility\\
  2. DaVinci Resolve を開き、Workspace > Scripts > editclone_resolve を実行

使い方:
  GUI が開くので、ログインしてインポートしたいジョブを選択してください。
  アクセストークンは Account ページから取得できます（1時間有効）。
"""

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

API_BASE = "https://editclone-production.up.railway.app"


# ---------------------------------------------------------------------------
# DaVinci Resolve 接続
# ---------------------------------------------------------------------------

def get_resolve():
    try:
        import DaVinciResolveScript as dvr  # type: ignore
        resolve = dvr.scriptapp("Resolve")
    except ImportError:
        for path in [
            "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/Scripts/Modules/",
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\\",
            "/opt/resolve/libs/Fusion/Scripts/Modules/",
        ]:
            sys.path.insert(0, path)
        try:
            import DaVinciResolveScript as dvr  # type: ignore
            resolve = dvr.scriptapp("Resolve")
        except ImportError:
            return None
    return resolve


# ---------------------------------------------------------------------------
# EditClone API
# ---------------------------------------------------------------------------

def api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def api_login(email: str, password: str) -> str:
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/plugin/auth/token",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["access_token"]


def download_edl(job_id: str, token: str, out_path: str) -> bool:
    req = urllib.request.Request(
        f"{API_BASE}/plugin/jobs/{job_id}/edl",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(out_path, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"EDL ダウンロードエラー: {e}")
        return False


def import_edl(resolve, edl_path: str, video_name: str) -> bool:
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    if not project:
        return False
    media_pool = project.GetMediaPool()
    timeline = media_pool.ImportTimelineFromFile(
        edl_path,
        {"timelineName": f"EditClone - {video_name}"},
    )
    return timeline is not None


# ---------------------------------------------------------------------------
# トークンキャッシュ
# ---------------------------------------------------------------------------

def load_cached_token() -> str:
    token_file = os.path.join(tempfile.gettempdir(), ".editclone_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read().strip()
        if token:
            try:
                api_get("/plugin/me", token)
                return token
            except Exception:
                pass
    return os.environ.get("EDITCLONE_TOKEN", "")


def save_cached_token(token: str):
    token_file = os.path.join(tempfile.gettempdir(), ".editclone_token")
    with open(token_file, "w") as f:
        f.write(token)


# ---------------------------------------------------------------------------
# GUI（tkinter）
# ---------------------------------------------------------------------------

def run_gui(resolve):
    try:
        import tkinter as tk
        from tkinter import font as tkfont
        from tkinter import ttk, messagebox
    except ImportError:
        print("tkinter が利用できません。コンソールモードで起動します。")
        run_console(resolve)
        return

    # カラーパレット（DaVinci 風ダークテーマ）
    BG = "#1c1c1e"
    PANEL = "#2c2c2e"
    ACCENT = "#f97316"  # オレンジ
    TEXT = "#f0f0f0"
    SUBTEXT = "#9a9a9a"
    SUCCESS = "#30d158"
    ERROR = "#ff453a"

    root = tk.Tk()
    root.title("EditClone for DaVinci Resolve")
    root.geometry("480x580")
    root.resizable(False, False)
    root.configure(bg=BG)

    try:
        root.tk.call("tk", "scaling", 1.5)
    except Exception:
        pass

    state = {"token": load_cached_token(), "jobs": []}

    # ----- ヘッダー -----
    header = tk.Frame(root, bg=ACCENT, height=52)
    header.pack(fill="x")
    header.pack_propagate(False)
    tk.Label(
        header, text="  EditClone × DaVinci Resolve",
        bg=ACCENT, fg="white", font=("Helvetica", 13, "bold"), anchor="w"
    ).pack(fill="y", side="left", padx=12)

    # ----- メインコンテナ -----
    main = tk.Frame(root, bg=BG, padx=20, pady=16)
    main.pack(fill="both", expand=True)

    # ----- ログインセクション -----
    login_frame = tk.LabelFrame(
        main, text=" ログイン / Token ", bg=PANEL, fg=SUBTEXT,
        font=("Helvetica", 9), bd=1, relief="flat", padx=12, pady=10
    )
    login_frame.pack(fill="x", pady=(0, 12))

    tk.Label(login_frame, text="アクセストークン (Account ページから取得)", bg=PANEL, fg=SUBTEXT,
             font=("Helvetica", 9)).pack(anchor="w")
    token_var = tk.StringVar(value=state["token"][:60] + "..." if len(state["token"]) > 60 else state["token"])
    token_entry = tk.Entry(login_frame, textvariable=token_var, bg="#3a3a3c", fg=TEXT,
                           insertbackground=TEXT, relief="flat", font=("Courier", 9), width=50)
    token_entry.pack(fill="x", pady=(4, 8))

    sep = tk.Label(login_frame, text="または", bg=PANEL, fg=SUBTEXT, font=("Helvetica", 9))
    sep.pack(anchor="w", pady=(0, 4))

    cred_frame = tk.Frame(login_frame, bg=PANEL)
    cred_frame.pack(fill="x")

    tk.Label(cred_frame, text="メール", bg=PANEL, fg=SUBTEXT, font=("Helvetica", 9), width=8, anchor="w").grid(row=0, column=0, sticky="w")
    email_var = tk.StringVar()
    tk.Entry(cred_frame, textvariable=email_var, bg="#3a3a3c", fg=TEXT, insertbackground=TEXT,
             relief="flat", font=("Helvetica", 10), width=32).grid(row=0, column=1, sticky="ew", pady=2)

    tk.Label(cred_frame, text="パスワード", bg=PANEL, fg=SUBTEXT, font=("Helvetica", 9), width=8, anchor="w").grid(row=1, column=0, sticky="w")
    pw_var = tk.StringVar()
    tk.Entry(cred_frame, textvariable=pw_var, bg="#3a3a3c", fg=TEXT, insertbackground=TEXT,
             relief="flat", font=("Helvetica", 10), width=32, show="•").grid(row=1, column=1, sticky="ew", pady=2)

    status_var = tk.StringVar()
    status_label = tk.Label(main, textvariable=status_var, bg=BG, fg=SUBTEXT, font=("Helvetica", 9), wraplength=440)
    status_label.pack(fill="x", pady=(0, 8))

    def set_status(msg, color=SUBTEXT):
        status_var.set(msg)
        status_label.configure(fg=color)
        root.update_idletasks()

    def do_login():
        token = token_var.get().strip()
        if not token:
            email = email_var.get().strip()
            pw = pw_var.get().strip()
            if not email or not pw:
                set_status("トークンかメール/パスワードを入力してください", ERROR)
                return
            set_status("ログイン中...")
            try:
                token = api_login(email, pw)
            except Exception as e:
                set_status(f"ログインエラー: {e}", ERROR)
                return

        set_status("ジョブ一覧を取得中...")
        try:
            api_get("/plugin/me", token)
            data = api_get("/plugin/jobs", token)
        except Exception as e:
            set_status(f"APIエラー: {e}", ERROR)
            return

        state["token"] = token
        save_cached_token(token)
        state["jobs"] = data.get("jobs", [])
        refresh_job_list()
        set_status(f"✓ ログイン済み  /  {len(state['jobs'])} 件のジョブ", SUCCESS)

    login_btn = tk.Button(
        login_frame, text="接続する", command=do_login,
        bg=ACCENT, fg="white", font=("Helvetica", 10, "bold"),
        relief="flat", padx=12, pady=6, cursor="hand2",
        activebackground="#ea6c00", activeforeground="white"
    )
    login_btn.pack(anchor="e", pady=(8, 0))

    # ----- ジョブ一覧 -----
    jobs_frame = tk.LabelFrame(
        main, text=" ジョブを選択 ", bg=PANEL, fg=SUBTEXT,
        font=("Helvetica", 9), bd=1, relief="flat", padx=8, pady=8
    )
    jobs_frame.pack(fill="both", expand=True, pady=(0, 12))

    job_listbox = tk.Listbox(
        jobs_frame, bg="#3a3a3c", fg=TEXT, selectbackground=ACCENT,
        selectforeground="white", font=("Helvetica", 10), relief="flat",
        bd=0, highlightthickness=0, activestyle="none", height=7
    )
    job_listbox.pack(fill="both", expand=True)

    def refresh_job_list():
        job_listbox.delete(0, "end")
        for j in state["jobs"][:15]:
            name = j.get("video_name") or j.get("filename", "unknown")
            date = j.get("created_at", "")[:10]
            job_listbox.insert("end", f"  {name}  ({date})")

    # ----- インポートボタン -----
    import_btn = tk.Button(
        main, text="DaVinci Resolve にインポート",
        command=lambda: do_import(),
        bg=ACCENT, fg="white", font=("Helvetica", 11, "bold"),
        relief="flat", pady=10, cursor="hand2",
        activebackground="#ea6c00", activeforeground="white",
        state="normal"
    )
    import_btn.pack(fill="x")

    def do_import():
        sel = job_listbox.curselection()
        if not sel:
            set_status("インポートするジョブを選択してください", ERROR)
            return
        if not state["token"]:
            set_status("先にログインしてください", ERROR)
            return

        job = state["jobs"][sel[0]]
        video_name = job.get("video_name") or job.get("filename", "video")
        job_id = job["job_id"]

        set_status(f"「{video_name}」の EDL をダウンロード中...")
        import_btn.configure(state="disabled")

        edl_fd, edl_path = tempfile.mkstemp(suffix=".edl")
        os.close(edl_fd)

        try:
            if not download_edl(job_id, state["token"], edl_path):
                set_status("EDL のダウンロードに失敗しました", ERROR)
                return

            set_status("タイムラインをインポート中...")
            if import_edl(resolve, edl_path, video_name):
                set_status(f"✓ 「EditClone - {video_name}」のインポート完了！", SUCCESS)
            else:
                set_status("インポートに失敗しました。元の動画をメディアプールに追加してから再試行してください。", ERROR)
        finally:
            try:
                os.unlink(edl_path)
            except OSError:
                pass
            import_btn.configure(state="normal")

    # 起動時にキャッシュトークンがあれば自動接続
    if state["token"]:
        root.after(200, do_login)

    root.mainloop()


# ---------------------------------------------------------------------------
# コンソールモード（tkinter が使えない場合のフォールバック）
# ---------------------------------------------------------------------------

def run_console(resolve):
    print("=" * 50)
    print("  EditClone — DaVinci Resolve Integration")
    print("=" * 50)

    token = load_cached_token()
    if not token:
        print("\nアクセストークンを入力するか、メール/パスワードでログインしてください。")
        choice = input("  [1] アクセストークン  [2] メール/パスワード : ").strip()
        if choice == "1":
            token = input("  トークン: ").strip()
        else:
            email = input("  メール: ").strip()
            pw = input("  パスワード: ").strip()
            try:
                token = api_login(email, pw)
                print("  ✅ ログイン成功")
            except Exception as e:
                print(f"  ❌ ログインエラー: {e}")
                sys.exit(1)
        save_cached_token(token)

    print("\n📡 ジョブ一覧を取得中...")
    try:
        data = api_get("/plugin/jobs", token)
    except Exception as e:
        print(f"❌ API エラー: {e}")
        sys.exit(1)

    jobs = data.get("jobs", [])
    if not jobs:
        print("完了済みのジョブがありません。")
        sys.exit(0)

    print("\n── 最近のジョブ ──────────────────────")
    for i, job in enumerate(jobs[:10], 1):
        name = job.get("video_name") or job.get("filename", "unknown")
        date = job.get("created_at", "")[:10]
        print(f"  {i:2d}. {name} ({date})")
    print("─────────────────────────────────────")

    raw = input(f"\nジョブ番号 (1-{min(len(jobs), 10)}, q で終了): ").strip()
    if raw.lower() == "q":
        sys.exit(0)
    try:
        idx = int(raw) - 1
        job = jobs[idx]
    except (ValueError, IndexError):
        print("無効な番号です")
        sys.exit(1)

    video_name = job.get("video_name") or job.get("filename", "video")
    print(f"\n📥 「{video_name}」の EDL をダウンロード中...")

    edl_fd, edl_path = tempfile.mkstemp(suffix=".edl")
    os.close(edl_fd)

    try:
        if not download_edl(job["job_id"], token, edl_path):
            sys.exit(1)
        print("🎬 タイムラインをインポート中...")
        if import_edl(resolve, edl_path, video_name):
            print(f"\n✅ 「EditClone - {video_name}」のインポート完了！")
        else:
            print("❌ インポートに失敗しました。元の動画をメディアプールに追加してから再試行してください。")
    finally:
        try:
            os.unlink(edl_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def main():
    resolve = get_resolve()
    if resolve is None:
        print("❌ DaVinci Resolve に接続できません。Resolve が起動しているか確認してください。")
        sys.exit(1)

    run_gui(resolve)


if __name__ == "__main__":
    main()
