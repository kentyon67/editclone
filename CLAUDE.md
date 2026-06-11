# CLAUDE.md — EditClone 開発ルール

---

## プロジェクト概要

**EditClone** — マルチ NLE 対応 AI 編集エージェント（Web アプリ + Plugin）

ユーザーが動画をアップロードし、プロンプト・参考動画・編集前後ペア・過去編集履歴を使って理想の編集を自動生成する。**使えば使うほど学習しパーソナライズされる**ことが最重要価値。Style Profile と Project Sync による学習ループが核心。

**最終ビジョン:** 元動画＋プロンプトだけで理想の完成動画を作れるAIエージェント。Plugin と連携することでさらに精度が上がる。

---

## 現在のフェーズ

| フェーズ | 状態 | 概要 |
|---------|------|------|
| Phase 1: Web v1 安定化 | ✅ 完了 | FastAPI・フロントエンド・Supabase・Stripe・Railway/Vercel デプロイ |
| Phase 2: Style Engine v1 | ✅ 完了 | Style Profile CRUD・参考動画・フィードバック・AI改善 |
| Phase 3: Project Sync | ✅ 完了 | Project/Revision モデル・再エクスポート・Plugin連携 |
| Phase 4: Rich Editing | ✅ 完了 | リッチFCPXML・Premiere XML・EDL・MP4・チャット編集 |
| Phase 5: Plugin | 🔄 コード完了・申請待ち | FCP/Premiere/DaVinci Plugin（DaVinci v5: チャット・エージェントチーム・暗黙的学習） |
| Phase 6: Learning & Marketplace | ✅ 完了 | 編集DNA・Marketplace・週次精度・チーム・外部API・Webhook |

→ 詳細は [docs/phases.md](docs/phases.md)

---

## 技術スタック

| 区分 | 技術 |
|------|------|
| Backend | Python 3.11 / FastAPI / Uvicorn |
| 動画処理 | ffmpeg / OpenCV |
| AI（文字起こし） | faster-whisper（CTranslate2） |
| AI（編集方針・Style Profile） | Claude API（Sonnet: 編集/合成, Haiku: エージェント/候補提案） |
| 出力 | FCPXML 1.10 / SRT / YouTubeチャプター / MP4 / Premiere XML / EDL |
| Frontend | Next.js 16 / React 19 / Tailwind CSS v4 |
| i18n | next-intl 4.x（日本語・英語） |
| 認証 | Supabase Auth（JWT） |
| DB | Supabase PostgreSQL |
| ストレージ | Supabase Storage（本番）/ ローカル（開発） |
| 課金 | Stripe Checkout + Webhook |
| ホスティング | Railway（Backend）/ Vercel（Frontend） |

---

## 収益モデル

| プラン | 月額 | 本数 | 最大時間 | Plugin | Project Sync |
|--------|------|------|---------|--------|-------------|
| Free | ¥0 | 月5本 | 5分 | 不可 | 不可 |
| Pro | ¥980 | 月30本 | 15分 | 不可 | 不可 |
| Creator | ¥2,980 | 月100本 | 60分 | 可 | 可 |
| Studio | ¥9,800 | 無制限 | 無制限 | 可（複数） | 可 |

---

## 開発ルール

### 設計上の最重要原則

1. **Web 単体で高機能アプリとして成立させる** — Plugin は「さらに理想に近づける」拡張であり必須ではない
2. **Style Profile と Project Sync は設計の核心** — 学習ループを壊す変更は行わない
3. **URL 参考動画は oEmbed のみ合法** — YouTube 等からの動画ダウンロードコードは書かない
4. **MP4 = 直接投稿用 / FCPXML・Premiere XML = 編集ソフトで調整用** — 混同しない

### 役割分担

**ユーザーが行う判断:** 機能要件・仕様・UX/デザイン・マーケティング・価格戦略・優先順位

**Claude が自動実行する作業（確認不要）:**
コード作成・編集・リファクタリング、パッケージ追加、テスト、Playwright E2E、バグ修正、git commit / git push、アプリ起動確認、Agent Teams による多角的評価と自動改善

### 必ず確認してから実行

- ファイル・フォルダの**削除**
- 本番 DB の直接操作・データ削除
- Stripe 本番モードへの切り替え
- Secret Key / API Key の変更・削除
- 破壊的な API 変更（後方互換性のない変更）

### コミット規則

プレフィックス: `docs` / `feat` / `fix` / `refactor` / `test` / `chore`

---

## 環境変数

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | Claude API キー | Backend |
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

- [フェーズ詳細](docs/phases.md) — Phase 1〜6 の全タスクテーブル
- [API一覧](docs/api.md) — 全エンドポイント一覧
- [仕様書](docs/specification.md)
- [ロードマップ](docs/roadmap.md)
- [アーキテクチャ](docs/architecture.md)
- [デプロイガイド](docs/deploy-guide.md)
