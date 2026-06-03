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

**Phase 0: ドキュメント整備中**（コード実装はまだ行っていません）

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

## セットアップ（将来予定）

```bash
git clone https://github.com/kentyon67/editclone.git
cd editclone
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## ライセンス

MIT
