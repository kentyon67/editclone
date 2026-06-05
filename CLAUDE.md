# CLAUDE.md — EditClone 開発ルール

このファイルはClaude Codeがプロジェクトを理解し、正しく作業するための開発ルール定義です。

---

## プロジェクト概要

**EditClone** — マルチ NLE 対応 AI 編集エージェント（Web アプリ + Plugin）

ユーザーが動画をアップロードし、プロンプト・参考動画・編集前後ペア・過去編集履歴を使って、理想に近い編集を自動生成する。

**最重要価値: 編集スタイルの学習・再現**
単なる自動カット・字幕ツールではない。使えば使うほど、ユーザーの編集スタイルを学習しパーソナライズされる。Style Profile と Project Sync による学習ループが核心。

**最終ビジョン:** 元動画＋プロンプト（＋参考動画）を送れば、AIが FCPXML / MP4 / Premiere XML レベルで最適な編集を自動実行。Plugin との連携でさらに精度が上がる。

---

## 現在のフェーズ

### Phase 1: Web v1 安定化 — 🔄 進行中

| 機能 | 状態 | ファイル |
|------|------|------|
| FastAPI基盤 + `/health` | ✅ | `app/main.py` |
| 動画アップロード | ✅ | `app/routers/videos.py` |
| 動画基本情報取得（OpenCV） | ✅ | `app/services/video_info.py` |
| Whisper文字起こし（faster-whisper） | ✅ | `app/services/transcription.py` |
| 無音検出（ffmpeg silencedetect） | ✅ | `app/services/silence.py` |
| カット提案 | ✅ | `app/services/cut_suggestion.py` |
| FCPXML生成（動画+ZIP） | ✅ | `app/services/fcpxml.py` |
| YouTubeチャプター生成 | ✅ | `app/services/chapters.py` |
| SRT字幕ファイル生成 | ✅ | `app/services/srt.py` |
| 非同期ジョブ処理 | ✅ | `app/services/jobs.py` |
| フロントエンド（Next.js 16・日英対応） | ✅ | `frontend/` |
| 全ページUI（Landing/Auth/Dashboard/Upload/Results/Pricing/Account） | ✅ | `frontend/app/[locale]/` |
| Supabase Auth バックエンド連携 | ✅ | `app/middleware/auth.py` |
| Supabase クラウドストレージ | ✅ | `app/services/storage.py` |
| Stripe Checkout + Webhook + Portal | ✅ | `app/routers/billing.py` |
| フロントエンド認証保護ルート | ✅ | `frontend/middleware.ts` |
| Railway バックエンドデプロイ | ✅ | `railway.json` |
| Vercel フロントエンドデプロイ | ✅ | `frontend/vercel.json` |
| MP4 出力（ffmpeg サーバーサイド） | ✅ | `app/services/mp4_render.py` |
| 利用回数制限（プランごと） | ✅ | `app/services/usage.py` |
| Analytics 基盤（Supabase ログ） | ✅ | `app/services/analytics.py` |
| フロントエンド i18n（マルチ NLE 対応コピー） | ✅ | `frontend/messages/` |
| 本番環境変数設定（Secret） | 🔄 | ユーザー手動設定待ち |
| Supabase schema.sql 実行 | 🔄 | ユーザー手動設定待ち |

### Phase 2: Style Engine v1 — ⏳ 未着手

| 機能 | 備考 |
|------|------|
| Style Profile CRUD | 編集スタイルの保存・管理 |
| 参考動画 URL 登録（oEmbed のみ） | 動画ダウンロードは禁止 |
| 参考動画ファイル分析 | カットテンポ・字幕密度・無音量 |
| Style Profile 生成・適用 | LLM（Claude API）連携 |
| 採用 / 却下フィードバック記録 | 学習ループの基盤 |

### Phase 3: Project Sync Foundation — ⏳ 未着手

| 機能 | 備考 |
|------|------|
| Project / ProjectRevision モデル | DB スキーマ追加 |
| Export 履歴・Sync Status 管理 | Web ↔ Plugin 同期基盤 |
| Conflict Handling 基本実装 | Plugin 優先・手動解決 |
| Sync API 設計 | Plugin 連携準備 |

### Phase 4: Rich Editing — ⏳ 未着手

| 機能 | 備考 |
|------|------|
| テロップスタイル反映 | FCPXML・Premiere XML |
| 画像・写真スライド動画化 | 画像素材対応 |
| ズーム演出・B-roll 提案 | 演出強化 |
| Premiere XML / DaVinci XML 出力 | マルチ NLE 対応 |

### Phase 5: Plugin 早期着手（Phase 2〜3 と並行） — ⏳ 未着手

| 機能 | 審査期間 | 備考 |
|------|---------|------|
| Premiere Plugin（UXP）設計・開発・申請 | Adobe: 2〜4 週間 | Phase 2 開始と同時着手 |
| Final Cut Extension 設計・開発・申請 | Apple: 1〜3 ヶ月 | Phase 2 開始と同時着手 |
| DaVinci Script / Panel 調査 | — | Phase 3 中 |
| CapCut 連携調査 | — | Phase 6 以降 |

### Phase 6: Learning & Marketplace — ⏳ 未着手

| 機能 | 備考 |
|------|------|
| 編集前後ペア分析（"編集DNA"抽出） | 業界最高レベルの差別化 |
| ユーザーフィードバック学習 | Plugin 修正データ活用 |
| Style Marketplace | 販売・購入・収益分配 |
| チーム共有・API 公開 | Studio プラン付加価値 |

---

## 技術スタック

| 区分 | 技術 |
|------|------|
| Backend | Python 3.11 / FastAPI / Uvicorn |
| 動画処理 | ffmpeg / OpenCV |
| AI（文字起こし） | faster-whisper（CTranslate2） |
| AI（編集方針・Style Profile） | Claude API |
| 出力 | FCPXML / SRT / YouTubeチャプター / MP4 / Premiere XML |
| Frontend | Next.js 16 / React 19 / Tailwind CSS v4 |
| i18n | next-intl 4.x（日本語・英語） |
| 認証 | Supabase Auth（JWT） |
| DB | Supabase PostgreSQL |
| ストレージ | Supabase Storage（本番）/ ローカル（開発） |
| 課金 | Stripe Checkout + Webhook |
| ホスティング | Railway（Backend）/ Vercel（Frontend） |
| MP4 レンダリング | ffmpeg.wasm（短動画）/ Modal（長動画） |

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

透かし（ウォーターマーク）なし。制限は量的制限のみ。

| プラン | 月額 | 本数 | 最大時間 | Plugin | Project Sync |
|--------|------|------|---------|--------|-------------|
| Free | ¥0 | 月3本 | 3分 | 不可 | 不可 |
| Pro | ¥980 | 月30本 | 15分 | 不可 | 不可 |
| Creator | ¥2,980 | 月100本 | 60分 | 可 | 可 |
| Studio | ¥9,800 | 無制限 | 無制限 | 可（複数） | 可 |

---

## 開発ルール

### 設計上の最重要原則

1. **Web 単体で高機能アプリとして成立させる**
   Plugin がなくても、全基本機能が Web で利用できること。Plugin は「さらに理想に近づける」拡張であり必須ではない。

2. **Style Profile と Project Sync は設計の核心**
   新機能実装前に、Style Profile と Project Sync への影響を確認すること。学習ループを壊す変更は行わない。

3. **MP4 出力は Phase 1 機能**
   MP4 出力は早期から実装する。短動画は ffmpeg.wasm（ブラウザ側）、長動画は Modal 等のサーバーレス従量課金で実装する。

4. **URL 参考動画は oEmbed のみ合法**
   YouTube / TikTok / Instagram 等からの動画ダウンロードコードは書かない。oEmbed API によるタイトル・サムネイル取得のみ許可。

5. **Plugin 審査期間を見越して早期着手**
   Phase 2 開始と同時に Plugin 設計・開発を始める。Apple 審査（1〜3 ヶ月）/ Adobe 審査（2〜4 週間）を逆算してスケジュールを立てる。

6. **完成動画 MP4 と編集プロジェクト出力の違いを明確にする**
   MP4 = 直接投稿用 / FCPXML・Premiere XML = 編集ソフトで調整用。混同しない。

### 通常作業（確認不要で進める）

- ファイル作成・編集
- ドキュメント更新（specification.md / roadmap.md / architecture.md / CLAUDE.md）
- 新機能の追加
- フロントエンドコンポーネントの変更

### 必ず確認してから実行

- ファイル・フォルダの削除
- 大規模リファクタリング
- Git 操作（commit / push / reset / rebase / force push）
- パッケージの追加・削除（requirements.txt / package.json）
- 破壊的な API 変更（既存フロントが壊れる変更）
- 本番環境への直接変更
- Stripe 本番モードへの切り替え
- Secret Key / API Key の操作

### 実装前の確認事項

- 新機能実装前に、関連 docs を更新する
- Style Profile・Project Sync との整合性を確認する
- Web 単体での動作を損なわないか確認する

### コミット規則

```
feat: add Style Profile CRUD
feat: add MP4 export via ffmpeg.wasm
feat: add Premiere XML output
fix: resolve PORT expansion in Railway startup
docs: redefine product requirements and roadmap
chore: add modal to requirements
```

プレフィックス: `docs` / `feat` / `fix` / `refactor` / `test` / `chore`

---

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `CORS_ORIGINS` | フロントエンドURL（カンマ区切り） | Backend |
| `WHISPER_MODEL` | tiny/base/small/medium | Backend |
| `SUPABASE_URL` | SupabaseプロジェクトURL | Backend |
| `SUPABASE_SERVICE_ROLE_KEY` | サービスロールキー（秘密・絶対公開禁止） | Backend |
| `STRIPE_SECRET_KEY` | Stripeシークレットキー（秘密） | Backend |
| `STRIPE_WEBHOOK_SECRET` | Webhook署名シークレット | Backend |
| `STRIPE_PRICE_PRO` | Pro プラン Price ID | Backend |
| `STRIPE_PRICE_CREATOR` | Creator プラン Price ID | Backend |
| `STRIPE_PRICE_STUDIO` | Studio プラン Price ID | Backend |
| `NEXT_PUBLIC_API_URL` | バックエンドURL | Frontend |
| `NEXT_PUBLIC_SUPABASE_URL` | SupabaseプロジェクトURL | Frontend |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase公開キー | Frontend |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe公開キー | Frontend |

---

## 関連ドキュメント

- [仕様書](docs/specification.md)
- [ロードマップ](docs/roadmap.md)
- [アーキテクチャ](docs/architecture.md)
- [デプロイガイド](docs/deploy-guide.md)
