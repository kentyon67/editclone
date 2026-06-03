# EditClone アーキテクチャ設計書

## 1. MVP構成の方針

- シンプルさ優先。複雑な構成は段階的に追加する
- MVPはFastAPI単体で動作する。データベース・認証・フロントエンドは不要
- 動画はローカルファイルシステムに保存する
- 各処理（文字起こし・無音検出・FCPXML生成）はサービスクラスとして分離する

---

## 2. MVPディレクトリ構成（予定）

```
editclone/
├── app/
│   ├── main.py               # FastAPIエントリポイント
│   ├── routers/
│   │   └── videos.py         # 動画関連ルーター
│   ├── services/
│   │   ├── video_info.py     # 動画基本情報取得（ffmpeg）
│   │   ├── transcription.py  # Whisper文字起こし
│   │   ├── silence.py        # 無音検出
│   │   ├── cut_suggestion.py # カット提案ロジック
│   │   └── fcpxml.py         # FCPXML生成
│   └── models/
│       └── schemas.py        # Pydanticスキーマ
├── uploads/                  # アップロードされた動画（Git管理外）
├── docs/
│   ├── specification.md
│   ├── roadmap.md
│   └── architecture.md
├── CLAUDE.md
├── README.md
└── requirements.txt
```

---

## 3. コンポーネント構成

```
[クライアント（curl / HTTPクライアント）]
        │ HTTP
        ▼
[FastAPI アプリ（app/main.py）]
        │
        ├── routers/videos.py
        │       │
        │       ├── services/video_info.py   ←── ffmpeg
        │       ├── services/transcription.py ←── Whisper / OpenAI API
        │       ├── services/silence.py       ←── ffmpeg / OpenCV
        │       ├── services/cut_suggestion.py
        │       └── services/fcpxml.py
        │
        └── uploads/ （ローカルファイルシステム）
```

---

## 4. データフロー（MVP）

### 動画アップロード〜FCPXML出力の全体フロー

```
1. POST /videos/upload
   └─ 動画ファイルをuploads/に保存
   └─ video_idを返す

2. POST /videos/{video_id}/transcribe
   └─ Whisperで音声をテキスト変換
   └─ タイムスタンプ付きセグメントを返す

3. POST /videos/{video_id}/detect-silence
   └─ ffmpegで無音区間を検出
   └─ 無音セグメント一覧を返す

4. POST /videos/{video_id}/suggest-cuts
   └─ 無音区間 + セリフ区切りからカット候補を生成
   └─ カット提案リストを返す

5. POST /videos/{video_id}/export-fcpxml
   └─ カット提案をFCPXML形式に変換
   └─ FCPXMLファイルをレスポンス
```

---

## 5. 技術スタック詳細

### Backend

| 技術 | 役割 |
|------|------|
| Python 3.11+ | 実装言語 |
| FastAPI | APIフレームワーク |
| Pydantic | リクエスト/レスポンスのバリデーション |
| Uvicorn | ASGIサーバー |

### 動画処理

| 技術 | 役割 |
|------|------|
| ffmpeg | 動画メタデータ取得・無音検出・フォーマット変換 |
| OpenCV | 映像フレーム解析（将来フェーズで活用） |
| MoviePy | 動画クリップ操作（将来フェーズで活用） |

### AI

| 技術 | 役割 |
|------|------|
| Whisper（ローカル）または OpenAI API | 音声文字起こし |
| Claude API / OpenAI API | 将来フェーズ：編集方針の生成・スタイル分析 |

### 出力

| 技術 | 役割 |
|------|------|
| FCPXML | Final Cut Proで読み込めるXML形式のプロジェクトファイル |

---

## 6. 将来フェーズの構成変更（予定）

### Phase 3以降で追加するコンポーネント

```
[Next.js フロントエンド]
        │ HTTP
        ▼
[FastAPI バックエンド]
        │
        ├── PostgreSQL（ユーザー・動画メタデータ・スタイル保存）
        ├── S3互換ストレージ（動画ファイル保存）
        └── Stripe（課金）
```

---

## 7. FCPXMLについて

FCPXMLはFinal Cut Proが定義するXML形式のプロジェクトファイルです。

- `.fcpxml` 拡張子
- タイムライン・クリップ・カット位置・テロップ・カラー補正を記述できる
- Final Cut ProのFile > Import > XMLで読み込み可能

EditCloneはカット提案をFCPXMLに変換することで、ユーザーがFinal Cut Proで即座に編集を開始できる状態を提供します。

---

## 8. 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式アーキテクチャ設計書初版作成 |
