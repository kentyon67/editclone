#!/usr/bin/env python3
"""
EditClone — DaVinci Resolve 連携スクリプト
==========================================

DaVinci Resolve のタイムラインに EditClone の編集結果をインポートします。

インストール方法:
  1. このファイルを以下のフォルダにコピーしてください:
     - macOS: ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/
     - Windows: C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Fusion\\Scripts\\Utility\\
  2. DaVinci Resolve を開き、Workspace > Scripts > editclone_resolve を実行

使い方:
  1. DaVinci Resolve でプロジェクトを開く
  2. このスクリプトを実行
  3. EditClone のアクセストークンを入力 (Account ページから取得)
  4. インポートしたいジョブを選択
  5. 「Import」を押す

注意:
  - メディアプールに元の動画が登録済みであることを確認してください
  - EDL のインポートには対応する動画ファイルが必要です
"""

import sys
import os
import json
import urllib.request
import urllib.error
import tempfile

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE = "https://editclone-production.up.railway.app"


# ---------------------------------------------------------------------------
# DaVinci Resolve connection
# ---------------------------------------------------------------------------
def get_resolve():
    """DaVinci Resolve インスタンスを取得する。"""
    try:
        import DaVinciResolveScript as dvr  # type: ignore
        resolve = dvr.scriptapp("Resolve")
    except ImportError:
        # スクリプトフォルダ外から実行する場合の代替ロード
        script_module = None
        candidates = [
            "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/Scripts/Modules/",
            r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\\",
            "/opt/resolve/libs/Fusion/Scripts/Modules/",
        ]
        for path in candidates:
            sys.path.insert(0, path)
        try:
            import DaVinciResolveScript as dvr  # type: ignore
            resolve = dvr.scriptapp("Resolve")
        except ImportError:
            print("❌ DaVinciResolveScript モジュールが見つかりません。")
            print("   スクリプトを Resolve の Scripts/Utility/ フォルダに配置してください。")
            return None

    if resolve is None:
        print("❌ DaVinci Resolve に接続できません。Resolve が起動しているか確認してください。")
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
    except urllib.error.HTTPError as e:
        print(f"❌ EDL ダウンロードエラー: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"❌ EDL ダウンロードエラー: {e}")
        return False


def login(email: str, password: str) -> str:
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/plugin/auth/token",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["access_token"]
    except urllib.error.HTTPError:
        raise ValueError("メールアドレスまたはパスワードが正しくありません")


# ---------------------------------------------------------------------------
# DaVinci import helpers
# ---------------------------------------------------------------------------
def import_edl(resolve, edl_path: str, video_name: str) -> bool:
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    if not project:
        print("❌ プロジェクトが開かれていません")
        return False

    media_pool = project.GetMediaPool()
    timeline = media_pool.ImportTimelineFromFile(
        edl_path,
        {"timelineName": f"EditClone - {video_name}"},
    )
    return timeline is not None


# ---------------------------------------------------------------------------
# UI (console)
# ---------------------------------------------------------------------------
def choose_job(jobs: list) -> dict | None:
    if not jobs:
        print("完了済みのジョブがありません。")
        return None

    print("\n── 最近のジョブ ──────────────────────")
    for i, job in enumerate(jobs[:10], 1):
        name = job.get("video_name") or job.get("filename", "unknown")
        date = job.get("created_at", "")[:10]
        print(f"  {i:2d}. {name} ({date})")
    print("─────────────────────────────────────")

    raw = input(f"\nインポートするジョブ番号 (1-{min(len(jobs), 10)}, q で終了): ").strip()
    if raw.lower() == "q":
        return None
    try:
        idx = int(raw) - 1
        return jobs[idx]
    except (ValueError, IndexError):
        print("無効な番号です")
        return None


def get_token_interactive() -> str:
    """トークンファイル → 環境変数 → 対話入力 の順に試みる。"""
    # 1. キャッシュファイル
    token_file = os.path.join(tempfile.gettempdir(), ".editclone_token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read().strip()
        if token:
            try:
                api_get("/plugin/me", token)
                return token
            except Exception:
                pass  # トークン期限切れ

    # 2. 環境変数
    token = os.environ.get("EDITCLONE_TOKEN", "")
    if token:
        return token

    # 3. 対話入力
    print("\n── EditClone ログイン ─────────────────")
    print("  Account ページのアクセストークンを入力するか、")
    print("  メール/パスワードでログインしてください。\n")
    choice = input("  [1] アクセストークンを直接入力  [2] メール/パスワード : ").strip()
    if choice == "1":
        token = input("  アクセストークン: ").strip()
    else:
        email = input("  メール: ").strip()
        pw = input("  パスワード: ").strip()
        token = login(email, pw)
        print("  ✅ ログイン成功")

    # キャッシュ保存
    with open(token_file, "w") as f:
        f.write(token)

    return token


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 50)
    print("  EditClone — DaVinci Resolve Integration")
    print("=" * 50)

    resolve = get_resolve()
    if resolve is None:
        sys.exit(1)

    token = get_token_interactive()

    print("\n📡 ジョブ一覧を取得中...")
    try:
        data = api_get("/plugin/jobs", token)
    except Exception as e:
        print(f"❌ API エラー: {e}")
        sys.exit(1)

    job = choose_job(data.get("jobs", []))
    if job is None:
        print("キャンセルしました。")
        sys.exit(0)

    video_name = job.get("video_name") or job.get("filename", "video")
    print(f"\n📥 「{video_name}」の EDL をダウンロード中...")

    edl_fd, edl_path = tempfile.mkstemp(suffix=".edl")
    os.close(edl_fd)

    try:
        if not download_edl(job["job_id"], token, edl_path):
            sys.exit(1)

        print("🎬 タイムラインをインポート中...")
        if import_edl(resolve, edl_path, video_name):
            print(f"\n✅ 「EditClone - {video_name}」タイムラインのインポート完了！")
            print("   ※ メディアが見つからない場合はメディアプールで再リンクしてください。")
        else:
            print("❌ インポートに失敗しました。")
            print("   ヒント: 元の動画をメディアプールに追加してから再試行してください。")
    finally:
        try:
            os.unlink(edl_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
