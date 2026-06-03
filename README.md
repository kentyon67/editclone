# EditClone

**AI編集アシスタント for Final Cut Pro**

EditCloneは、動画の編集スタイルをAIが分析し、Final Cut Pro用プロジェクト（FCPXML）として出力するツールです。
YouTuber・ショート動画制作者が、自分や参考動画の編集スタイルを再現した編集ファイルをゼロから作る手間を省きます。

## コア価値

**「編集スタイルの再現」** — 単なるAI自動編集ではなく、あなたや参考動画のスタイルをそのまま新しい動画に適用する。

## 想定ユーザー

- YouTuber / TikToker / ショート動画制作者
- 動画編集フリーランス
- Final Cut Proユーザー

## 現在のフェーズ

**Phase 1: MVP実装中**（FastAPI基盤）

## MVPの機能範囲

1. 動画アップロード
2. 動画の基本情報取得（ファイル名・サイズ・長さ）
3. Whisperによる文字起こし
4. 無音区間の検出
5. 自動カット提案
6. 簡易FCPXML生成

## 技術スタック

| 区分 | 技術 |
|------|------|
| Backend | Python / FastAPI |
| 動画処理 | ffmpeg / OpenCV / MoviePy |
| AI | Whisper / OpenAI API |
| 出力形式 | FCPXML |

## ドキュメント

- [仕様書](docs/specification.md)
- [ロードマップ](docs/roadmap.md)
- [アーキテクチャ](docs/architecture.md)
- [開発ルール](CLAUDE.md)

## セットアップ

```bash
git clone https://github.com/kentyon67/editclone.git
cd editclone

# 仮想環境の作成・有効化
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 依存パッケージのインストール
pip install -r requirements.txt

# サーバー起動
uvicorn app.main:app --reload
```

起動後、以下で動作確認できます。

```bash
# ヘルスチェック
curl http://localhost:8000/health

# 動画アップロード（.mp4 / .mov / .m4v）
curl -F "file=@your_video.mp4" http://localhost:8000/videos/upload

# 動画情報取得（アップロード後に返ったvideo_idを使う）
curl http://localhost:8000/videos/info/{video_id}

# 文字起こし（初回はWhisperモデル約145MBが自動ダウンロードされる）
curl -X POST http://localhost:8000/videos/transcribe/{video_id}

# モデルサイズ変更（デフォルト: base）
# tiny=75MB / base=145MB / small=461MB / medium=1.5GB
WHISPER_MODEL=small uvicorn app.main:app --reload

# API仕様（Swagger UI）
# ブラウザで http://localhost:8000/docs を開く
```

## ライセンス

MIT
