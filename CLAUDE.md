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

### Phase 1: Web v1 安定化 — ✅ 完了

| 機能 | 状態 | ファイル |
|------|------|------|
| FastAPI基盤 + `/health` | ✅ | `app/main.py` |
| 動画アップロード | ✅ | `app/routers/videos.py` |
| 動画基本情報取得（OpenCV） | ✅ | `app/services/video_info.py` |
| Whisper文字起こし（faster-whisper） | ✅ | `app/services/transcription.py` |
| 無音検出（ffmpeg silencedetect） | ✅ | `app/services/silence.py` |
| カット提案 | ✅ | `app/services/cut_suggestion.py` |
| FCPXML生成（字幕 caption lane 付き） | ✅ | `app/services/fcpxml.py` |
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
| Claude API 編集指示（プロンプト → セマンティックカット） | ✅ | `app/services/ai_edit.py` |
| NLE プラグイン直接インポート（FCP/Premiere/DaVinci） | ✅ | `plugins/` |
| Supabase ジョブ永続化（Railway 再起動耐性） | ✅ | `app/services/jobs.py` |
| NTSC ドロップフレームタイムコード（29.97fps） | ✅ | `app/services/fcpxml.py`, `premiere_xml.py`, `edl.py` |
| ダッシュボード処理履歴表示（全ステータス） | ✅ | `frontend/app/[locale]/dashboard/` |
| 本番環境変数設定（Secret） | 🔄 | ユーザー手動設定待ち |
| Supabase schema.sql v5 実行 | 🔄 | ユーザー手動設定待ち |

### Phase 2: Style Engine v1 — ✅ 完了

| 機能 | 状態 | ファイル |
|------|------|------|
| Style Profile CRUD | ✅ | `app/services/style_profiles.py`, `app/routers/style_profiles.py` |
| 参考動画 URL 登録（oEmbed のみ） | ✅ | `app/services/style_profiles.py` |
| フィードバック記録（accept/partial/reject） | ✅ | `app/services/style_profiles.py` |
| AI Profile 改善提案（Claude API） | ✅ | `app/services/style_profiles.py` |
| フィードバック統計 API | ✅ | `GET /style-profiles/{id}/stats` |
| Styles ページ UI（参考動画・AI改善・stats表示） | ✅ | `frontend/app/[locale]/styles/` |

### Phase 3: Project Sync Foundation — ✅ 実装済み

| 機能 | 状態 | ファイル |
|------|------|------|
| Project / ProjectRevision モデル | ✅ | `supabase/schema.sql` v5 |
| Export 履歴・Sync Status 管理 | ✅ | `app/services/projects.py` |
| ジョブ完了時プロジェクト自動作成 | ✅ | `app/services/jobs.py` |
| プロジェクト詳細ページ | ✅ | `frontend/app/[locale]/projects/[id]/` |
| 再エクスポート（同設定で再処理） | ✅ | `POST /projects/{id}/re-export` |
| Plugin リビジョン受信 + 競合検出 | ✅ | `POST /projects/{id}/revisions` |
| Dashboard プロジェクトリンク | ✅ | `frontend/app/[locale]/dashboard/` |
| Results ページプロジェクトリンク | ✅ | `frontend/app/[locale]/results/` |

### Phase 4: Rich Editing — ✅ 大半完了

| 機能 | 状態 | ファイル |
|------|------|------|
| FCPXML 字幕 caption lane | ✅ | `app/services/fcpxml.py` |
| NTSC ドロップフレームタイムコード（29.97fps） | ✅ | `fcpxml.py`, `premiere_xml.py`, `edl.py` |
| Premiere Pro XML 出力（XMEML） | ✅ | `app/services/premiere_xml.py` |
| DaVinci EDL 出力 | ✅ | `app/services/edl.py` |
| Caption Style カスタマイズ（フォント・位置・色・太字） | ✅ | `app/services/mp4_render.py`, `app/routers/style_profiles.py` |
| Style Profile → MP4 字幕焼き込み連動 | ✅ | `app/services/jobs.py` |
| Style Profile → FCPXML テキストスタイル反映 | ✅ | `app/services/fcpxml.py` |
| Premiere XML への字幕マーカー追加 | ✅ | `app/services/premiere_xml.py` |
| ZIP 構造整理（fcp/premiere/davinci/subtitles/media） | ✅ | `app/services/jobs.py` |
| カット点音声クロスフェード（20ms afade） | ✅ | `app/services/mp4_render.py` |
| AI カット粒度改善（raw_segments 使用） | ✅ | `app/services/jobs.py` |
| AI 編集プロンプト改善（英日対応・フィラーリスト） | ✅ | `app/services/ai_edit.py` |
| 画像・写真スライド動画化 | ✅ | `app/services/slideshow.py`, `app/routers/videos.py` |
| ズーム演出（subtle 5% / punch 10%） | ✅ | `app/services/mp4_render.py` |
| B-roll 提案 | ✅ | `app/services/broll.py`, `GET /jobs/{id}/broll-suggestions` |

### Phase 5: Plugin 早期着手 — 🔄 コード完了・申請待ち

| Plugin | コード | 申請 | 審査期間 |
|--------|--------|------|---------|
| FCP Extension（Swift/SwiftUI WKWebView） | ✅ `plugins/fcp-extension/` | ⏳ 未申請 | Apple: 1〜3 ヶ月 |
| Premiere CEP Panel（HTML/JS） | ✅ `plugins/premiere-cep/` | ⏳ 未申請 | Adobe: 2〜4 週間 |
| DaVinci Script（Python） | ✅ `plugins/davinci-script/` | — | 申請不要（配布のみ） |

### Phase 6: Learning & Marketplace — 🔄 着手済み

| 機能 | 状態 | ファイル |
|------|------|------|
| 編集前後ペア分析（"編集DNA"抽出） | ✅ | `app/services/edit_dna.py`, `POST /style-profiles/analyze-pair` |
| 編集DNA UI（/styles/analyze） | ✅ | `frontend/app/[locale]/styles/analyze/` |
| フィードバック自動学習（5件ごと自動改善） | ✅ | `app/services/style_profiles.py` |
| Plugin revision diff → フィードバック自動記録 | ✅ | `app/services/projects.py` |
| Style Marketplace（公開・コピー・タグ） | ✅ | `app/services/style_profiles.py`, `app/routers/style_profiles.py`, `frontend/app/[locale]/styles/marketplace/` |
| マーケット評価・レビュー（星評価・分布） | ✅ | `app/services/style_profiles.py`, `frontend/app/[locale]/styles/marketplace/` |
| パーソナライズ精度の定量評価（週次accept率・トレンド） | ✅ | `app/services/style_profiles.py`, `GET /style-profiles/{id}/accuracy` |
| チーム招待・権限管理（Studio プラン） | ✅ | `app/services/teams.py`, `app/routers/teams.py`, `frontend/app/[locale]/account/` |
| チーム招待承認ページ | ✅ | `frontend/app/[locale]/teams/invite/[token]/` |
| 精度メトリクスUI（週次accept率グラフ） | ✅ | `frontend/app/[locale]/styles/` AccuracySection |
| B-roll 提案UI（resultsページ表示） | ✅ | `frontend/app/[locale]/results/[jobId]/` |
| 外部 API 公開（APIキー管理） | ✅ | `app/services/api_keys.py`, `app/routers/api_keys.py`, `GET/POST/DELETE /api-keys` |
| Webhook 連携（job.completed/failed） | ✅ | `app/services/webhooks.py`, `app/routers/webhooks.py`, HMAC署名付き配信 |

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
