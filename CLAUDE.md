# CLAUDE.md — EditClone 開発ルール

このファイルはClaude Codeがプロジェクトを理解し、正しく作業するための開発ルール定義です。

---

## プロジェクト概要

**EditClone** — Final Cut Pro向けAI編集アシスタント

ユーザーが動画をアップロードすると、AIが編集スタイルを分析し、新しい動画に同様のスタイルを適用したFinal Cut Pro用プロジェクトファイル（FCPXML）を生成する。

**最重要価値: 編集スタイルの再現**
単なるAI自動編集ではなく、「あなたや参考動画の編集スタイルをそのまま再現する」ことが最大の差別化ポイント。

---

## MVP範囲

以下のみを対象にする。それ以外は実装しない。

1. FastAPI最小構成
2. `GET /health`
3. 動画アップロード（ローカル保存）
4. 動画基本情報取得（ファイル名・サイズ・長さ）
5. Whisper文字起こし
6. 無音検出
7. 簡単なカット提案
8. 簡易FCPXML生成

---

## MVPで実装しないもの

- ユーザー認証
- 課金機能
- PostgreSQL
- フロントエンド（Next.js）
- BGM提案 / 効果音提案 / カラー補正
- 編集前後ペア分析
- モデル動画スタイル学習
- 独自機械学習モデル

---

## 最終構想

詳細は [docs/specification.md](docs/specification.md) を参照。

主要な将来機能:
- モデル動画によるスタイル学習
- 編集前後動画ペアの差分分析
- テロップ・ズーム・BGM・効果音・カラー補正の提案
- ユーザーごとの編集スタイル保存
- ユーザー管理・課金（Free / Pro / Creator / Studio）

---

## 技術スタック

| 区分 | 技術 |
|------|------|
| Backend | Python 3.11+ / FastAPI / Pydantic / Uvicorn |
| 動画処理 | ffmpeg / OpenCV / MoviePy |
| AI | Whisper または OpenAI API（文字起こし） |
| 将来AI | Claude API / OpenAI API（編集方針生成） |
| 出力 | FCPXML |
| 将来DB | PostgreSQL |
| 将来Frontend | Next.js |

---

## 開発ルール

### 基本方針

- 小さい単位で実装する。1回の作業で大量の機能を追加しない
- まず動くものを作る。完璧な設計より動作確認優先
- 仕様書（docs/specification.md）を更新してから実装する
- 実装後は必ず「変更ファイル・実行方法・確認方法」を報告する

### 禁止事項（必ず確認してから実行）

- ファイルの削除（git管理外ファイルも含む）
- 大規模リファクタリング
- Git操作（commit / push / reset / rebase 等）
- パッケージの追加・削除（requirements.txt変更）
- 破壊的なAPI変更

### 実装単位の原則

- 1機能 = 1コミット
- 機能をまたいだ変更は分割する
- リファクタリングは機能追加と同一コミットに混ぜない

---

## コミット方針

機能ごとに小さくコミットする。コミットメッセージ例:

```
docs: define project vision and MVP
feat: add FastAPI health endpoint
feat: add video upload endpoint
feat: extract video metadata
feat: add transcription service
feat: add silence detection
feat: generate cut suggestions
feat: generate basic FCPXML
```

プレフィックス:
- `docs:` — ドキュメントのみの変更
- `feat:` — 新機能追加
- `fix:` — バグ修正
- `refactor:` — 動作を変えないコード変更（事前確認必須）
- `test:` — テスト追加・修正
- `chore:` — ビルド・依存関係の変更

---

## 実装順序

Phase 0（現在）→ Phase 1 → Phase 2 → Phase 3 → Phase 4

詳細は [docs/roadmap.md](docs/roadmap.md) を参照。

**Phase 1の実装順序（MVP）:**
1. FastAPI基盤 + `/health`
2. 動画アップロード
3. 動画基本情報取得
4. Whisper文字起こし
5. 無音検出
6. カット提案
7. FCPXML生成

---

## 関連ドキュメント

- [仕様書](docs/specification.md) — 機能仕様・API仕様・収益モデル
- [ロードマップ](docs/roadmap.md) — フェーズ別タスク一覧
- [アーキテクチャ](docs/architecture.md) — ディレクトリ構成・コンポーネント設計
