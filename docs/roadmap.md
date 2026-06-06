# EditClone ロードマップ

バージョン: 2.0.0  
最終更新: 2026-06-06

---

## フェーズ概要

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | Web v1 安定化（デプロイ・MP4・制限・Analytics） | ✅ 完了 |
| Phase 2 | Style Engine v1（Style Profile 生成・適用） | ✅ 完了 |
| Phase 3 | Project Sync Foundation | ✅ 完了 |
| Phase 4 | Rich Editing（テロップ・Premiere XML・EDL・Caption Style） | ✅ 完了 |
| Phase 5 | Plugin 早期着手（Phase 2〜3 と並行） | 🔄 コード完了・未申請 |
| Phase 6 | Learning & Marketplace | 🔄 着手済み |

---

## Phase 1: Web v1 安定化 ✅

- [x] Railway バックエンドデプロイ
- [x] Vercel フロントエンドデプロイ
- [x] Supabase Auth 連携（JWT 検証ミドルウェア）
- [x] Supabase Storage 連携
- [x] Supabase ジョブ永続化（Railway 再起動耐性）
- [x] Stripe Checkout / Webhook / Portal
- [x] 動画アップロード → 文字起こし → 無音検出 → FCPXML → ZIP
- [x] 非同期ジョブ処理（BackgroundTasks）
- [x] MP4 出力（ffmpeg filter_complex trim+concat + 字幕焼き込み）
- [x] プランごとの利用回数・時間制限
- [x] Analytics 基盤（Supabase ログ）
- [x] フロントエンド全ページ（Landing/Auth/Dashboard/Upload/Results/Pricing/Account）
- [x] i18n 日英対応（next-intl）
- [x] 処理結果インライン MP4 プレーヤー（results ページ）

---

## Phase 2: Style Engine v1 ✅

- [x] Style Profile CRUD（作成・編集・削除・アクティブ切替）
- [x] 参考動画 URL 登録（YouTube / Vimeo oEmbed のみ）
- [x] フィードバック記録（accept / partial / reject）
- [x] フィードバック統計（accept率・件数）
- [x] AI Profile 改善提案（Claude API / claude-sonnet-4-6）
- [x] Style Profile 選択時の設定自動反映（noise_db / min_silence / prompt）
- [x] Styles ページ UI（参考動画・AI改善・stats表示）

---

## Phase 3: Project Sync Foundation ✅

- [x] Project / ProjectRevision モデル（supabase/schema.sql v5）
- [x] ジョブ完了時プロジェクト自動作成
- [x] Export 履歴・Sync Status 管理
- [x] Plugin リビジョン受信 + 競合検出
- [x] 再エクスポート（POST /projects/{id}/re-export）
- [x] プロジェクト詳細ページ
- [x] Dashboard + Results ページへのプロジェクトリンク

---

## Phase 4: Rich Editing ✅（大半完了）

**完了済み:**
- [x] FCPXML 字幕 caption lane（FCP でテキストトラックとして読み込み）
- [x] NTSC ドロップフレームタイムコード（29.97fps 対応）
- [x] Premiere Pro XML 出力（XMEML 形式）
- [x] DaVinci EDL 出力（ドロップフレーム対応）
- [x] Caption Style カスタマイズ（フォントサイズ・位置・色・太字）
- [x] Style Profile → MP4 字幕焼き込みへの反映
- [x] ZIP 構造整理（fcp/ + premiere/ + davinci/ + subtitles/ + media/）

**完了済み（追加）:**
- [x] カット点での音声クロスフェード（各セグメントに 20ms afade を付与）
- [x] テロップスタイルの FCPXML への反映（font_size / color / bold → text-style-def）
- [x] Premiere XML への字幕マーカー追加（セグメントをシーケンスマーカーとして埋め込み）
- [x] AI カット粒度改善（Whisper raw_segments 使用で細粒度カットが可能に）
- [x] AI 編集プロンプト改善（英日バイリンガル対応・フィラーワードリスト追加）

**追加完了:**
- [x] 画像・写真スライドショー動画化（POST /videos/slideshow + /upload/slideshow UI）
- [x] DaVinci Script に tkinter GUI 設定追加（初回起動時にダイアログ）

**追加完了:**
- [x] ズーム演出（subtle 5% / punch 10% 中央クロップズームイン）

**完了済み（追加）:**
- [x] B-roll 提案（Claude API トランスクリプト分析 → 挿入ポイント + キーワード提案）
- [x] B-roll 提案 UI（Results ページにインライン表示・優先度バッジ・タイムスタンプ）

---

## Phase 5: Plugin 早期着手 🔄（コード完了・申請待ち）

Apple App Store 審査: 1〜3 ヶ月 / Adobe Marketplace 審査: 2〜4 週間

### FCP Extension（fcp-extension/）

- [x] Swift/SwiftUI WKWebView ベース（Full Web UI）
- [x] `window.editcloneBridge / editcloneNLE / editcloneAgent` inject
- [x] FCPXML 認証付きダウンロード（Bearer トークン）
- [x] NSWorkspace.shared.open で FCP 直接起動
- [x] **AI Agent ブリッジ**: `agentEdit` → ポーリング → 自動 FCPXML インポート
- [x] **Style Profile ブリッジ**: `getStyleProfiles` / `activateStyleProfile`
- [x] **リビジョン送信**: `sendRevision` → サーバー学習ループ
- [ ] macOS 実機テスト・署名
- [ ] Mac App Store 申請（Apple Developer Program 登録必要）

### Premiere CEP（premiere-cep/）

- [x] CEP Panel（HTML/JS）
- [x] iframe で Web アプリをロード（?nle=premiere）
- [x] postMessage → Premiere XML 認証付きダウンロード
- [x] ExtendScript での Premiere インポート
- [ ] Windows 実機テスト
- [ ] Adobe Exchange 申請

### Premiere UXP（premiere/）— 🆕 完全 Agent リデザイン

- [x] **3タブ Agent UI**: ジョブ / AI編集 / スタイル
- [x] **AI編集タブ**: 自然言語指示 → `agent-edit` API → ポーリング → 自動インポート
- [x] **クイックプロンプト**: 冒頭カット・フィラー除去・告知カット・テンポ強化
- [x] **スタイルタブ**: プロファイル一覧・アクティブ切替
- [x] **ジョブタブ**: 再編集ボタン → AI編集タブへジャンプ
- [x] SRT 直接ダウンロード（`/plugin/jobs/{id}/srt`）
- [ ] Windows 実機テスト
- [ ] Adobe Exchange 申請

### DaVinci Script（davinci-script/）— 🆕 Agent GUI リデザイン

- [x] Python tkinter 多タブ Agent GUI
- [x] **AI編集タブ**: テキスト入力 → API → ポーリング → 自動インポート
- [x] **スタイルタブ**: プロファイル一覧・アクティブ切替
- [x] **設定タブ**: URL / トークン + 接続テスト
- [x] ZIP ダウンロード → 永続パスに保存 → FCPXML タイムライン自動生成
- [ ] 実機テスト（DaVinci Resolve 18+）

---

## Phase 6: Learning & Marketplace 🔄（着手済み）

**目標:** AI 学習ループの完成と収益拡大

### 6-1. 編集前後ペア分析（最重要差別化機能）✅

- [x] 編集前動画 + 編集後動画のペアアップロード（POST /style-profiles/analyze-pair）
- [x] 無音閾値・カット頻度・削除割合・平均セグメント長の抽出
- [x] 推奨 noise_db / min_silence / AI プロンプトの自動生成
- [x] Style Profile への適用 API（POST /style-profiles/{id}/apply-dna）
- [x] 編集 DNA 分析 UI（/styles/analyze ページ）

### 6-2. ユーザーフィードバック学習 ✅

- [x] 採用 / 却下データの蓄積（feedback_logs テーブル）
- [x] フィードバック 5 件ごとの自動プロンプト改善（record_feedback → _auto_refine_profile）
- [x] Plugin revision diff → フィードバック自動記録（`_learn_from_plugin_revision`）
- [x] パーソナライズ精度の定量評価（週次 accept 率推移・トレンド分析）

### 6-3. Style Marketplace ✅（基盤完了）

- [x] Style Profile 公開 / 非公開切替（POST /{id}/publish, unpublish）
- [x] 公開プロファイル閲覧（GET /marketplace, タグフィルタ）
- [x] プロファイルコピー（POST /marketplace/{id}/copy）
- [x] タグ付け（YouTube, TikTok, Podcast など 10 種類）
- [x] copy_count によるランキング
- [x] フロントエンド マーケットプレイスページ（/styles/marketplace）
- [x] 評価・レビュー（星評価 1〜5・コメント・分布グラフ）
- [ ] 購入・Creator 収益分配
- [ ] ジャンル別ランキング強化

### 6-4. チーム・API

- [x] チーム招待・権限管理（Studio プラン: 招待・承認・削除・ロール管理）
- [x] チームスタイルプロファイル共有（チームオーナーのプロファイルをメンバーが利用可能）
- [x] チーム招待承認ページ（/teams/invite/{token} — メールアドレス検証・エラーハンドリング）
- [x] 外部 API 公開（APIキー管理: eck_プレフィックス・SHA256ハッシュ保管・X-Api-Keyヘッダー認証）
- [x] Webhook 連携（job.completed/job.failed イベント・HMAC-SHA256シグネチャ付き配信）

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式ロードマップ初版（最終更新: 2026-06-06） |
| 2026-06-04 | 1.0.0 | 6 フェーズ構成に改定 |
| 2026-06-06 | 2.0.0 | Phase 1-4 完了・Phase 5 コード完了を反映。残タスクを明確化 |
| 2026-06-06 | 2.1.0 | Phase 4 完了（スライドショー）・Phase 6 着手（編集DNA・自動学習） |
| 2026-06-06 | 2.2.0 | Phase 4 ズーム演出・Phase 6-2 Plugin revision学習・Phase 6-3 マーケットプレイス基盤 |
| 2026-06-06 | 2.3.0 | Phase 5 Plugin Agent化完了: Premiere UXP 3タブAgent・DaVinci Agent GUI・FCP Agentブリッジ・Plugin API拡張 |
| 2026-06-06 | 2.4.0 | Phase 4完了: B-roll提案（Claude API）。Phase 6-2: 精度メトリクス（週次accept率・トレンド）。Phase 6-3: 星評価・レビューシステム。Phase 6-4: チーム招待・Studio権限管理。Schema v7 |
| 2026-06-06 | 2.5.0 | Phase 6-4完全完了: 外部APIキー管理（eck_プレフィックス・X-Api-Key認証）・Webhook連携（HMAC署名）・チーム招待承認ページ。B-roll UI（Resultsページ）。精度メトリクスUI（Stylesページ）。Schema v8 |
