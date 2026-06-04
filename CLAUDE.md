# CLAUDE.md — EditClone 開発ルール

このファイルはClaude Codeがプロジェクトを理解し、正しく作業するための開発ルール定義です。

---

## プロジェクト概要

**EditClone** — Final Cut Pro向けAI編集アシスタント（Webアプリ）

ユーザーが動画をアップロードすると、AIが編集スタイルを分析し、Final Cut Pro用プロジェクトファイル（FCPXML）・字幕（SRT）・チャプターを自動生成する。

**最重要価値: 編集スタイルの再現**
単なるAI自動編集ではなく、「あなたや参考動画の編集スタイルをそのまま再現する」ことが最大の差別化ポイント。

**最終ビジョン:** 元動画＋プロンプト（＋理想動画）を送れば、AIがFCPXMLレベルで最適な編集を自動実行。利用者が使うほどパーソナライズされる編集スタイルAI。

---

## 現在のフェーズ: Phase 2（公開準備・課金統合）

### Phase 1（MVP）— 完了済み ✅

| 機能 | ファイル |
|------|------|
| FastAPI基盤 + `/health` | `app/main.py` |
| 動画アップロード | `app/routers/videos.py` |
| 動画基本情報取得（OpenCV） | `app/services/video_info.py` |
| Whisper文字起こし（faster-whisper） | `app/services/transcription.py` |
| 無音検出（ffmpeg silencedetect） | `app/services/silence.py` |
| カット提案 | `app/services/cut_suggestion.py` |
| FCPXML生成（動画+ZIP） | `app/services/fcpxml.py` |
| YouTubeチャプター生成 | `app/services/chapters.py` |
| SRT字幕ファイル生成 | `app/services/srt.py` |
| 非同期ジョブ処理 | `app/services/jobs.py` |
| フロントエンド（Next.js 14・日英対応） | `frontend/` |
| 全ページUI（Landing/Auth/Dashboard/Upload/Results/Pricing/Account） | `frontend/app/[locale]/` |

### Phase 2（公開準備）— 実装中 🔄

| 機能 | 状態 | ファイル |
|------|------|------|
| Supabase DB スキーマ | 🔄 | `supabase/schema.sql` |
| Supabase認証バックエンド連携 | 🔄 | `app/middleware/auth.py` |
| Supabaseクラウドストレージ | 🔄 | `app/services/storage.py` |
| Stripe Checkout + Webhook | 🔄 | `app/routers/billing.py` |
| プランごとの使用量制限 | 🔄 | `app/routers/videos.py` |
| フロントエンド認証保護ルート | 🔄 | `frontend/middleware.ts` |
| Railwayデプロイ（Backend） | ⏳ | `railway.json` |
| Vercelデプロイ（Frontend） | ⏳ | `frontend/vercel.json` |

### Phase 3（コア差別化）— 未実装

| 機能 | 優先度 | 備考 |
|------|--------|------|
| モデル動画スタイル学習 | 最高 | EditCloneの最大差別化 |
| 編集前後ペア分析（"編集DNA"抽出） | 最高 | 業界初レベル |
| サムネイル候補フレーム抽出 | 高 | 顔検出・明るさ判定 |
| フィラー語除去（「えー」「あの」特化） | 高 | Whisper区間 + 精密カット |
| マルチNLEエクスポート（Premiere XML） | 中 | 市場3倍拡大 |
| 処理完了メール通知 | 中 | Supabase Edge Functions |
| APIアクセス（開発者向け） | 低 | Pro+プランの付加価値 |

### Phase 4（最終ビジョン）— 将来

- AI対話型編集指示（プロンプト + 動画 → FCPXML）
- テロップ・ズーム・BGM・効果音・カラー補正提案
- FCP拡張機能（Workflow Extension）
- ユーザーごとの編集スタイル自動学習・保存
- マルチカメラ対応

---

## 技術スタック（現在）

| 区分 | 技術 |
|------|------|
| Backend | Python 3.11+ / FastAPI / Uvicorn |
| 動画処理 | ffmpeg / OpenCV |
| AI | faster-whisper（文字起こし） |
| 将来AI | Claude API / OpenAI Vision API |
| 出力 | FCPXML + SRT + YouTubeチャプター（ZIP） |
| Frontend | Next.js 14 / React / Tailwind CSS |
| i18n | next-intl（日本語・英語） |
| 認証 | Supabase Auth |
| DB | Supabase PostgreSQL |
| ストレージ | Supabase Storage（本番）/ ローカル（開発） |
| 課金 | Stripe Checkout + Webhook |
| ホスティング | Railway（Backend）+ Vercel（Frontend） |

---

## APIエンドポイント一覧

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/health` | ヘルスチェック | 不要 |
| POST | `/videos/upload` | 動画アップロード | 必要 |
| GET | `/videos/info/{id}` | 動画基本情報 | 必要 |
| POST | `/videos/transcribe/{id}` | Whisper文字起こし | 必要 |
| POST | `/videos/detect-silence/{id}` | 無音検出 | 必要 |
| POST | `/videos/suggest-cuts/{id}` | カット提案 | 必要 |
| POST | `/videos/generate-fcpxml/{id}` | FCPXML+動画ZIP | 必要 |
| POST | `/videos/chapters/{id}` | YouTubeチャプター | 必要 |
| POST | `/videos/export-srt/{id}` | SRT字幕 | 必要 |
| POST | `/videos/process/{id}` | 全処理（非同期） | 必要 |
| GET | `/jobs/{job_id}` | ジョブステータス | 必要 |
| GET | `/jobs/{job_id}/download` | 結果ZIPダウンロード | 必要 |
| POST | `/billing/create-checkout` | Stripe Checkout作成 | 必要 |
| POST | `/billing/webhook` | Stripe Webhook受信 | 不要（署名検証） |
| GET | `/billing/portal` | Stripe顧客ポータル | 必要 |

---

## 収益モデル

| プラン | 月額 | 上限 |
|--------|------|------|
| Free | ¥0 / $0 | 月3本 |
| Pro | ¥980 / $9 | 月30本 |
| Creator | ¥2,980 / $29 | 月100本 |
| Studio | ¥9,800 / $99 | 無制限 |

---

## 開発ルール

### 通常作業（確認不要で進める）

- ファイル作成・編集
- README・ドキュメント更新
- 新機能の追加
- フロントエンドコンポーネントの変更

### 必ず確認してから実行

- ファイル・フォルダの削除
- 大規模リファクタリング
- Git操作（commit / push / reset / rebase）
- パッケージの追加・削除（requirements.txt / package.json）
- 破壊的なAPI変更（既存フロントが壊れる変更）
- 本番環境への直接変更

### コミット規則

```
feat: add Supabase auth middleware
feat: add Stripe billing endpoints
fix: resolve upload path on Railway
chore: add supabase and stripe to requirements
```

プレフィックス: `docs` / `feat` / `fix` / `refactor` / `test` / `chore`

---

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `CORS_ORIGINS` | フロントエンドURL（カンマ区切り） | Backend |
| `WHISPER_MODEL` | tiny/base/small/medium | Backend |
| `SUPABASE_URL` | SupabaseプロジェクトURL | Backend |
| `SUPABASE_SERVICE_ROLE_KEY` | サービスロールキー（秘密） | Backend |
| `STRIPE_SECRET_KEY` | Stripeシークレットキー（秘密） | Backend |
| `STRIPE_WEBHOOK_SECRET` | Webhook署名シークレット | Backend |
| `STRIPE_PRICE_PRO` | Pro プラン Price ID | Backend |
| `STRIPE_PRICE_CREATOR` | Creator プラン Price ID | Backend |
| `STRIPE_PRICE_STUDIO` | Studio プラン Price ID | Backend |
| `NEXT_PUBLIC_API_URL` | バックエンドURL | Frontend |
| `NEXT_PUBLIC_SUPABASE_URL` | SupabaseプロジェクットURL | Frontend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase公開キー | Frontend |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe公開キー | Frontend |

---

## 関連ドキュメント

- [仕様書](docs/specification.md)
- [ロードマップ](docs/roadmap.md)
- [アーキテクチャ](docs/architecture.md)
- [デプロイガイド](docs/deploy-guide.md)
