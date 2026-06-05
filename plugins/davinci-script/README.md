# EditClone — DaVinci Resolve Integration Script

## 概要

DaVinci Resolve の Scripts メニューから実行し、EditClone で処理した動画を
自動的に DaVinci のメディアプールとタイムラインにインポートするスクリプトです。

**審査不要・今すぐ配布可能。**

## インストール

### 1. スクリプトをコピー

| OS | パス |
|----|------|
| macOS | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/` |
| Windows | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\` |
| Linux | `~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/` |

`editclone_import.py` を上記ディレクトリにコピーする。

### 2. API トークンを設定

1. EditClone ウェブアプリ → アカウントページ → API キー（実装予定）
2. `editclone_import.py` を開き、以下を変更:

```python
EDITCLONE_API_URL = "https://your-backend.railway.app"  # 本番 URL
EDITCLONE_API_TOKEN = "your-jwt-token-here"
```

### 3. DaVinci Resolve を再起動

**Workspace > Scripts > Utility > editclone_import** が表示される。

## 使い方

1. DaVinci Resolve で新規プロジェクトを開く
2. EditClone ウェブアプリで動画を処理し、ジョブ ID をコピー
3. `Workspace > Scripts > Utility > editclone_import` を実行
4. ジョブ ID を入力して Enter
5. 自動でメディアプールにインポートされ、タイムラインが作成される

## 動作フロー

```
スクリプト実行
  └─ EditClone API からジョブ情報を取得
       └─ ZIP (FCPXML + メディア + SRT) をダウンロード
            └─ ~/Movies/EditClone/{job_id}/ に保存
                 └─ DaVinci メディアプールにインポート
                      └─ FCPXML からタイムライン生成
```

## 今後の改善予定

- GUI ダイアログでジョブを選択できるようにする
- EditClone ウェブアプリからワンクリックで DaVinci を起動してインポート
- タイムラインの自動カット適用
- SRT 字幕の自動キャプションレイヤー追加

## 必要な DaVinci Resolve バージョン

- DaVinci Resolve 17 以上（Python API サポート）
- Python 3.6 以上（DaVinci 付属の Python でも動作）
