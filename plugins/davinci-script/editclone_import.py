#!/usr/bin/env python3
"""
EditClone — DaVinci Resolve Integration Script
================================================
DaVinci Resolve の Scripts メニューから実行すると、
EditClone API から最新の完成ジョブを取得して
現在のプロジェクトにインポートします。

インストール方法:
  macOS: ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
  Windows: %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\
  Linux: ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/

使い方:
  DaVinci Resolve → Workspace → Scripts → EditClone Import
"""

import os
import sys
import json
import tempfile
import zipfile
import urllib.request
import urllib.error
from pathlib import Path

# ================================================================
# ユーザー設定 — 初回実行前に変更してください
# ================================================================

EDITCLONE_API_URL = "https://your-backend.railway.app"  # Railway バックエンド URL
EDITCLONE_API_TOKEN = ""  # Supabase JWT トークン（ウェブアプリでログイン後に取得）

# ================================================================


def get_resolve():
    """DaVinci Resolve Python API を取得する。"""
    try:
        import DaVinciResolveScript as dvr_script
        return dvr_script.scriptapp("Resolve")
    except ImportError:
        pass

    # DaVinci Resolve 付属の Python ライブラリのパスを追加
    resolve_paths = [
        "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/",
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\\",
        "/opt/resolve/libs/Fusion/",
    ]
    for path in resolve_paths:
        if os.path.exists(path) and path not in sys.path:
            sys.path.insert(0, path)
    try:
        import DaVinciResolveScript as dvr_script
        return dvr_script.scriptapp("Resolve")
    except ImportError:
        return None


def api_get(endpoint: str) -> dict:
    """EditClone API に GET リクエストを送る。"""
    url = f"{EDITCLONE_API_URL}{endpoint}"
    req = urllib.request.Request(url)
    if EDITCLONE_API_TOKEN:
        req.add_header("Authorization", f"Bearer {EDITCLONE_API_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def download_file(url: str, dest_path: Path) -> bool:
    """URL からファイルをダウンロードする。"""
    req = urllib.request.Request(url)
    if EDITCLONE_API_TOKEN:
        req.add_header("Authorization", f"Bearer {EDITCLONE_API_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dest_path.write_bytes(resp.read())
        return True
    except urllib.error.URLError as e:
        print(f"Download failed: {e}")
        return False


def extract_zip(zip_path: Path, dest_dir: Path) -> dict:
    """ZIP を展開して含まれるファイルのパスを返す。"""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)

    result = {"fcpxml": None, "media": [], "srt": None}
    for f in dest_dir.rglob("*"):
        if f.suffix == ".fcpxml":
            result["fcpxml"] = str(f)
        elif f.suffix in {".mp4", ".mov", ".m4v", ".mxf"}:
            result["media"].append(str(f))
        elif f.suffix == ".srt":
            result["srt"] = str(f)
    return result


def import_to_resolve(resolve, files: dict) -> str:
    """
    DaVinci Resolve にファイルをインポートする。
    メディア → メディアプールへ追加、タイムライン自動生成。
    """
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject()
    if not project:
        return "No active project"

    media_pool = project.GetMediaPool()
    root_bin = media_pool.GetRootFolder()

    # EditClone ビンを作成（なければ）
    editclone_bin = None
    for subfolder in root_bin.GetSubFolderList():
        if subfolder.GetName() == "EditClone":
            editclone_bin = subfolder
            break
    if editclone_bin is None:
        editclone_bin = media_pool.AddSubFolder(root_bin, "EditClone")

    media_pool.SetCurrentFolder(editclone_bin)

    # メディアファイルをインポート
    imported_clips = []
    if files["media"]:
        clips = media_pool.ImportMedia(files["media"])
        if clips:
            imported_clips = clips
            print(f"Imported {len(clips)} media file(s)")

    # SRT 字幕をインポート（あれば）
    if files["srt"]:
        try:
            media_pool.ImportMedia([files["srt"]])
            print("Imported SRT subtitles")
        except Exception:
            pass

    # FCPXML からタイムライン生成
    if files["fcpxml"]:
        timelines = media_pool.ImportTimelineFromFile(files["fcpxml"])
        if timelines:
            print(f"Imported timeline from FCPXML: {files['fcpxml']}")
            # 作成したタイムラインをアクティブに
            project.SetCurrentTimeline(timelines[0])
            return "ok"
        else:
            # FCPXML インポートが失敗した場合、メディアからタイムラインを作成
            if imported_clips:
                timeline = media_pool.CreateTimelineFromClips("EditClone", imported_clips)
                if timeline:
                    return "ok_no_xml"
            return "timeline_import_failed"

    return "ok_media_only"


def show_dialog(message: str):
    """DaVinci の UI ダイアログを表示する（利用可能な場合）。"""
    try:
        fusion = bmd.scriptapp("Fusion")
        if fusion:
            fusion.ShowCustomScriptDialog({
                "msg": message,
                "width": 400,
                "height": 100,
            })
            return
    except Exception:
        pass
    print(message)


def main():
    print("EditClone Import — Starting...")

    # 設定チェック
    if not EDITCLONE_API_TOKEN:
        msg = (
            "EditClone API トークンが設定されていません。\n"
            "editclone_import.py の EDITCLONE_API_TOKEN を設定してください。\n"
            "トークンの取得: EditClone ウェブアプリ → アカウント → API キー"
        )
        show_dialog(msg)
        return

    # DaVinci Resolve への接続
    resolve = get_resolve()
    if not resolve:
        show_dialog("DaVinci Resolve に接続できませんでした。Resolve が起動しているか確認してください。")
        return

    print("Connected to DaVinci Resolve")

    # 最新ジョブを取得
    try:
        usage = api_get("/usage/me")
        print(f"Plan: {usage.get('plan')} | Used: {usage.get('used')}/{usage.get('limit')}")
    except Exception as e:
        show_dialog(f"EditClone API に接続できません: {e}\nAPI URL と Token を確認してください。")
        return

    # 完了済みジョブ一覧を取得
    try:
        jobs_resp = api_get("/plugin/jobs")
        jobs_list = jobs_resp.get("jobs", [])
    except Exception as e:
        show_dialog(f"ジョブ一覧の取得に失敗しました: {e}")
        return

    if not jobs_list:
        show_dialog("完了済みジョブが見つかりません。\nEditClone ウェブアプリで動画を処理してください。")
        return

    # 最新のジョブを自動選択（1件のみの場合）または一覧表示
    if len(jobs_list) == 1:
        job_id = jobs_list[0]["job_id"]
        print(f"最新ジョブを自動選択: {jobs_list[0]['video_name']} ({job_id[:8]}...)")
    else:
        print("\n=== EditClone 完了済みジョブ一覧 ===")
        for i, j in enumerate(jobs_list[:10]):
            print(f"  [{i+1}] {j['video_name']} — {j['created_at'][:10]} ({j['job_id'][:8]}...)")
        print()
        try:
            choice = input("インポートするジョブ番号を入力してください [1]: ").strip()
            idx = int(choice) - 1 if choice else 0
            if idx < 0 or idx >= len(jobs_list):
                print("無効な番号です。1 番を使用します。")
                idx = 0
        except ValueError:
            idx = 0
        job_id = jobs_list[idx]["job_id"]
        print(f"選択: {jobs_list[idx]['video_name']} ({job_id[:8]}...)")

    print(f"Job ID: {job_id}")

    # ZIP をダウンロードして展開
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        zip_path = tmpdir_path / f"{job_id}_editclone.zip"

        print("Downloading ZIP...")
        download_url = f"{EDITCLONE_API_URL}/jobs/{job_id}/download"
        if not download_file(download_url, zip_path):
            show_dialog("ZIP のダウンロードに失敗しました。")
            return

        print("Extracting ZIP...")
        extract_dir = tmpdir_path / "extracted"
        extract_dir.mkdir()
        files = extract_zip(zip_path, extract_dir)
        print(f"Found: FCPXML={files['fcpxml']}, Media={files['media']}, SRT={files['srt']}")

        # ファイルを永続的な場所にコピー（tmpdir が消えるため）
        persist_dir = Path.home() / "Movies" / "EditClone" / job_id
        persist_dir.mkdir(parents=True, exist_ok=True)

        if files["fcpxml"]:
            import shutil
            dest = persist_dir / Path(files["fcpxml"]).name
            shutil.copy2(files["fcpxml"], dest)
            files["fcpxml"] = str(dest)

        if files["media"]:
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

        print(f"Files saved to: {persist_dir}")

        # DaVinci にインポート
        print("Importing to DaVinci Resolve...")
        result = import_to_resolve(resolve, files)

        if result.startswith("ok"):
            msg = f"✓ インポート完了！\n保存先: {persist_dir}"
            show_dialog(msg)
            print(msg)
        else:
            msg = f"インポート結果: {result}\n手動でファイルを開いてください: {persist_dir}"
            show_dialog(msg)
            print(msg)


if __name__ == "__main__":
    main()
