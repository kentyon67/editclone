# EditClone API エンドポイント一覧

## 基本

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/health` | ヘルスチェック | 不要 |

## 動画処理

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| POST | `/videos/upload` | 動画アップロード | 必要 |
| GET | `/videos/info/{id}` | 動画基本情報 | 必要 |
| POST | `/videos/transcribe/{id}` | Whisper文字起こし | 必要 |
| POST | `/videos/detect-silence/{id}` | 無音検出 | 必要 |
| POST | `/videos/suggest-cuts/{id}` | カット提案 | 必要 |
| POST | `/videos/generate-fcpxml/{id}` | FCPXML+動画ZIP | 必要 |
| POST | `/videos/chapters/{id}` | YouTubeチャプター | 必要 |
| POST | `/videos/export-srt/{id}` | SRT字幕 | 必要 |
| POST | `/videos/process/{id}` | 全処理（非同期） | 必要 |
| POST | `/videos/slideshow` | 画像スライドショー動画 | 必要 |

## ジョブ管理

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/jobs` | ジョブ一覧 | 必要 |
| GET | `/jobs/{id}` | ジョブステータス | 必要 |
| GET | `/jobs/{id}/download` | 結果ZIPダウンロード | 必要 |
| GET | `/jobs/{id}/mp4` | MP4ダウンロード | 必要 |
| GET | `/jobs/{id}/premiere-xml` | Premiere XMLダウンロード | 必要 |
| GET | `/jobs/{id}/edl` | EDLダウンロード | 必要 |
| GET | `/jobs/{id}/thumbnail` | サムネイルJPEG | 必要 |
| GET | `/jobs/{id}/broll-suggestions` | B-roll挿入提案 | 必要 |
| POST | `/jobs/{id}/refine` | Webインタラクティブ編集（チャット） | 必要 |
| GET | `/jobs/{id}/refine/fcpxml` | リファイン版FCPXML即時生成 | 必要 |
| GET | `/jobs/{id}/refine/suggestions` | AIプロンプト候補5件提案（Haiku） | 必要 |

## Style Profile

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/style-profiles` | プロファイル一覧 | 必要 |
| POST | `/style-profiles` | プロファイル作成 | 必要 |
| GET | `/style-profiles/active` | アクティブプロファイル取得 | 必要 |
| GET | `/style-profiles/{id}` | プロファイル詳細 | 必要 |
| PUT | `/style-profiles/{id}` | プロファイル更新 | 必要 |
| DELETE | `/style-profiles/{id}` | プロファイル削除 | 必要 |
| POST | `/style-profiles/{id}/activate` | アクティブに設定 | 必要 |
| GET | `/style-profiles/{id}/stats` | フィードバック統計 | 必要 |
| GET | `/style-profiles/{id}/accuracy` | 週次accept率・トレンド | 必要 |
| POST | `/style-profiles/{id}/ai-refine` | AI改善提案 | 必要 |
| POST | `/style-profiles/{id}/apply-dna` | DNA分析結果を適用 | 必要 |
| POST | `/style-profiles/{id}/publish` | Marketplaceに公開 | 必要 |
| POST | `/style-profiles/{id}/unpublish` | 公開停止 | 必要 |
| GET | `/style-profiles/{id}/reference-videos` | 参考動画一覧 | 必要 |
| POST | `/style-profiles/{id}/reference-videos` | 参考動画追加（oEmbed） | 必要 |
| DELETE | `/style-profiles/{id}/reference-videos/{vid}` | 参考動画削除 | 必要 |
| POST | `/style-profiles/feedback` | フィードバック記録 | 必要 |
| POST | `/style-profiles/analyze-pair` | 編集前後ペア分析（DNA抽出） | 必要 |
| GET | `/style-profiles/marketplace` | 公開プロファイル一覧 (`tag`, `q`) | 必要 |
| GET | `/style-profiles/marketplace/{id}` | 公開プロファイル詳細 | 必要 |
| POST | `/style-profiles/marketplace/{id}/copy` | プロファイルをコピー | 必要 |
| POST | `/style-profiles/marketplace/{id}/review` | レビュー投稿 | 必要 |
| GET | `/style-profiles/marketplace/{id}/reviews` | レビュー一覧・統計 | 必要 |

## プロジェクト

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/projects` | プロジェクト一覧 | 必要 |
| GET | `/projects/{id}` | プロジェクト詳細 | 必要 |
| POST | `/projects/{id}/re-export` | 再エクスポート | 必要 |
| POST | `/projects/{id}/revisions` | Pluginリビジョン受信 | 必要 |

## 課金

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| POST | `/billing/create-checkout` | Stripe Checkout作成 | 必要 |
| POST | `/billing/webhook` | Stripe Webhook受信 | 不要（署名検証） |
| GET | `/billing/portal` | Stripe顧客ポータル | 必要 |

## API Keys / Webhook

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/api-keys` | APIキー一覧 | 必要 |
| POST | `/api-keys` | APIキー発行 | 必要 |
| DELETE | `/api-keys/{id}` | APIキー削除 | 必要 |
| GET | `/webhooks` | Webhook一覧 | 必要 |
| POST | `/webhooks` | Webhook登録 | 必要 |
| DELETE | `/webhooks/{id}` | Webhook削除 | 必要 |

## チーム

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| GET | `/teams` | チーム一覧 | 必要 |
| POST | `/teams` | チーム作成 | 必要 |
| POST | `/teams/{id}/invite` | メンバー招待 | 必要 |
| POST | `/teams/invites/{token}/accept` | 招待承認 | 必要 |

## Plugin専用

| Method | Path | 機能 | 認証 |
|--------|------|------|------|
| POST | `/plugin/auth/token` | email/password → JWT | 不要 |
| GET | `/plugin/me` | ユーザー情報 | 必要 |
| GET | `/plugin/jobs` | 完了ジョブ一覧 | 必要 |
| GET | `/plugin/jobs/{id}/poll` | ジョブポーリング | 必要 |
| GET | `/plugin/jobs/{id}/details` | ジョブ詳細（トランスクリプト・カット） | 必要 |
| GET | `/plugin/jobs/{id}/fcpxml` | FCPXML取得 | 必要 |
| GET | `/plugin/jobs/{id}/premiere-xml` | Premiere XML取得 | 必要 |
| GET | `/plugin/jobs/{id}/edl` | EDL取得 | 必要 |
| GET | `/plugin/jobs/{id}/srt` | SRT取得 | 必要 |
| POST | `/plugin/jobs/{id}/agent-edit` | エージェント再編集 | 必要 |
| POST | `/plugin/jobs/{id}/chat-edit` | チャット編集（単一エージェント） | 必要 |
| POST | `/plugin/jobs/{id}/team-edit` | チャット編集（エージェントチーム） | 必要 |
| POST | `/plugin/jobs/{id}/rich-fcpxml` | リッチFCPXML生成 | 必要 |
| POST | `/plugin/jobs/{id}/rich-premiere-xml` | リッチPremiere XML生成 | 必要 |
| GET | `/plugin/style-profiles` | スタイル一覧 | 必要 |
| POST | `/plugin/style-profiles/{id}/activate` | スタイルをアクティブに | 必要 |
