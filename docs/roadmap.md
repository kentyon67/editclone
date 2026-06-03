# EditClone ロードマップ

## フェーズ概要

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 0 | ドキュメント整備・仕様確定 | 🔄 進行中 |
| Phase 1 | MVP実装（FastAPI + 基本機能） | 未着手 |
| Phase 2 | 編集スタイル分析（コア差別化機能） | 未着手 |
| Phase 3 | フロントエンド・ユーザー管理 | 未着手 |
| Phase 4 | 課金・スケーリング | 未着手 |

---

## Phase 0: ドキュメント整備（現在）

**目標:** 仕様・方針・アーキテクチャをチームとAIが共有できる状態にする

- [x] リポジトリ作成
- [x] 開発環境セットアップ（Git）
- [ ] 正式仕様書作成（specification.md）
- [ ] ロードマップ作成（roadmap.md）
- [ ] アーキテクチャ設計書作成（architecture.md）
- [ ] 開発ルール定義（CLAUDE.md）
- [ ] コミット: `docs: define project vision and MVP`

---

## Phase 1: MVP実装

**目標:** 動画をアップロードし、カット提案とFCPXMLを生成する最小動作版

### 1-1. FastAPI基盤

- [ ] FastAPIプロジェクト構成作成
- [ ] `GET /health` 実装
- [ ] コミット: `feat: add FastAPI health endpoint`

### 1-2. 動画アップロード

- [ ] `POST /videos/upload` 実装
- [ ] アップロードファイルのローカル保存
- [ ] コミット: `feat: add video upload endpoint`

### 1-3. 動画基本情報取得

- [ ] ffmpegで動画メタデータ取得
- [ ] `GET /videos/{video_id}/info` 実装
- [ ] コミット: `feat: extract video metadata`

### 1-4. Whisper文字起こし

- [ ] Whisper（またはOpenAI API）連携
- [ ] `POST /videos/{video_id}/transcribe` 実装
- [ ] コミット: `feat: add transcription service`

### 1-5. 無音検出

- [ ] ffmpegまたはOpenCVで無音区間検出
- [ ] `POST /videos/{video_id}/detect-silence` 実装
- [ ] コミット: `feat: add silence detection`

### 1-6. カット提案

- [ ] 無音区間・セリフ区切りからカット候補生成
- [ ] `POST /videos/{video_id}/suggest-cuts` 実装
- [ ] コミット: `feat: generate cut suggestions`

### 1-7. FCPXML生成

- [ ] FCPXMLテンプレート設計
- [ ] カット提案をFCPXML形式に変換
- [ ] `POST /videos/{video_id}/export-fcpxml` 実装
- [ ] Final Cut Proでの読み込み確認
- [ ] コミット: `feat: generate basic FCPXML`

---

## Phase 2: 編集スタイル分析（コア差別化機能）

**目標:** 編集スタイルの「再現」を実現し、競合との差別化を確立する

### 2-1. モデル動画スタイル学習

- [ ] モデル動画アップロード機能
- [ ] スタイル特徴量の抽出（カットリズム・テンポ・無音比率等）
- [ ] コミット: `feat: add model video style analysis`

### 2-2. 編集前後ペア差分分析

- [ ] 編集前動画と編集後動画のペアアップロード
- [ ] カット位置・テロップ・演出を差分として抽出
- [ ] コミット: `feat: add before/after pair analysis`

### 2-3. 編集スタイルの適用

- [ ] 抽出したスタイルを新しい動画に適用
- [ ] スタイルをユーザーごとに保存
- [ ] コミット: `feat: apply editing style to new video`

### 2-4. 追加提案機能

- [ ] テロップ位置・内容の提案
- [ ] ズーム演出の提案
- [ ] BGM提案（Claude/OpenAI APIを活用）
- [ ] 効果音配置の提案
- [ ] カラー補正提案

---

## Phase 3: フロントエンド・ユーザー管理

**目標:** 一般ユーザーが使えるWebアプリとして公開できる状態にする

- [ ] Next.jsフロントエンド構築
- [ ] 動画アップロードUI
- [ ] 結果表示UI（カット提案・FCPXML出力）
- [ ] ユーザー認証（メール or Google OAuth）
- [ ] PostgreSQLへのデータ永続化
- [ ] コミット群: `feat: add frontend`, `feat: add user auth`, etc.

---

## Phase 4: 課金・スケーリング

**目標:** サブスクリプション型サービスとして収益化する

- [ ] Stripe連携による課金機能
- [ ] プラン管理（Free / Pro / Creator / Studio）
- [ ] 利用制限の実装（月N本まで）
- [ ] クラウドストレージへの動画保存（S3等）
- [ ] 本番環境デプロイ

---

## 変更履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式ロードマップ初版作成 |
