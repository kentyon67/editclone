# EditClone — フェーズ進捗詳細

## Phase 1: Web v1 安定化 — ✅ 完了

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

## Phase 2: Style Engine v1 — ✅ 完了

| 機能 | 状態 | ファイル |
|------|------|------|
| Style Profile CRUD | ✅ | `app/services/style_profiles.py`, `app/routers/style_profiles.py` |
| 参考動画 URL 登録（oEmbed のみ） | ✅ | `app/services/style_profiles.py` |
| フィードバック記録（accept/partial/reject） | ✅ | `app/services/style_profiles.py` |
| AI Profile 改善提案（Claude API） | ✅ | `app/services/style_profiles.py` |
| フィードバック統計 API | ✅ | `GET /style-profiles/{id}/stats` |
| Styles ページ UI（参考動画・AI改善・stats表示） | ✅ | `frontend/app/[locale]/styles/` |

## Phase 3: Project Sync Foundation — ✅ 実装済み

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

## Phase 4: Rich Editing — ✅ 完了

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
| インタラクティブ編集（Web チャット /jobs/{id}/refine） | ✅ | `app/routers/jobs.py`, `app/services/jobs.py` |
| リッチ FCPXML（speed/transition/text/audio/color） | ✅ | `app/services/fcpxml.py` |

## Phase 5: Plugin 早期着手 — 🔄 コード完了・申請待ち

| Plugin | コード | 申請 | 審査期間 |
|--------|--------|------|---------|
| FCP Extension（Swift/SwiftUI WKWebView） | ✅ `plugins/fcp-extension/` | ⏳ 未申請 | Apple: 1〜3 ヶ月 |
| Premiere CEP Panel（HTML/JS） | ✅ `plugins/premiere-cep/` | ⏳ 未申請 | Adobe: 2〜4 週間 |
| DaVinci Script（Python） | ✅ `plugins/davinci-script/` | — | 申請不要（配布のみ） |

DaVinci Plugin v5 主な機能:
- 🎬 AI編集タブ（ファイル選択・アップロード・タイムライン自動生成）
- 💬 チャットタブ（11操作タイプ + エージェントチーム + FCPXML自動インポート）
- 🎨 スタイルタブ（Style Profile 管理）
- ⚙️ 設定タブ（API URL / Token / 診断）
- 暗黙的学習（使用するたびに自動フィードバック）

## Phase 6: Learning & Marketplace — ✅ 実装済み

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
| Webhook 連携（job.completed/failed + 指数バックオフリトライ） | ✅ | `app/services/webhooks.py`, `app/routers/webhooks.py` |
| AIプロンプト候補提案（Haiku） | ✅ | `GET /jobs/{id}/refine/suggestions` |
| サムネイル抽出 | ✅ | `GET /jobs/{id}/thumbnail` |
| Marketplace テキスト検索 | ✅ | `GET /style-profiles/marketplace?q=` |
| 学習済みプロンプトパターン表示 | ✅ | `frontend/app/[locale]/styles/` PromptPatternsSection |
| ダッシュボードサムネイル | ✅ | `frontend/app/[locale]/dashboard/` |
