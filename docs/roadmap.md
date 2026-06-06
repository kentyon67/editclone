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
| Phase 4 | Rich Editing（テロップ・Premiere XML・EDL・Caption Style） | ✅ 大半完了 |
| Phase 5 | Plugin 早期着手（Phase 2〜3 と並行） | 🔄 コード完了・未申請 |
| Phase 6 | Learning & Marketplace | ⏳ 未着手 |

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

**残タスク:**
- [ ] 画像・写真スライド動画化
- [ ] ズーム演出・B-roll 提案

---

## Phase 5: Plugin 早期着手 🔄（コード完了・申請待ち）

Apple App Store 審査: 1〜3 ヶ月 / Adobe Marketplace 審査: 2〜4 週間

### FCP Extension（fcp-extension/）

- [x] Swift/SwiftUI WKWebView ベース
- [x] `window.editcloneBridge = true` inject
- [x] `window.editcloneNLE = 'fcp'` inject
- [x] FCPXML 認証付きダウンロード（Bearer トークン）
- [x] NSWorkspace.shared.open で FCP 直接起動
- [ ] macOS 実機テスト・署名
- [ ] Mac App Store 申請（Apple Developer Program 登録必要）

### Premiere CEP（premiere-cep/）

- [x] CEP Panel（HTML/JS）
- [x] iframe で Web アプリをロード（?nle=premiere）
- [x] postMessage → Premiere XML 認証付きダウンロード
- [x] ExtendScript での Premiere インポート
- [ ] Windows 実機テスト
- [ ] Adobe Exchange 申請

### DaVinci Script（davinci-script/）

- [x] Python スクリプト（Fusion Scripts/Utility に配置）
- [x] 完了ジョブ一覧取得 + 選択
- [x] ZIP ダウンロード → FCPXML タイムライン自動生成
- [ ] ユーザー設定の GUI 化（現状はファイル直接編集が必要）
- [ ] 実機テスト（DaVinci Resolve 18+）

---

## Phase 6: Learning & Marketplace ⏳（未着手）

**目標:** AI 学習ループの完成と収益拡大

### 6-1. 編集前後ペア分析（最重要差別化機能）

- [ ] 編集前動画 + 編集後動画のペアアップロード
- [ ] カット位置・テロップ・演出の差分抽出
- [ ] Style Profile への自動反映
- [ ] 「編集 DNA」生成（ユーザーごとの編集パターン）

### 6-2. ユーザーフィードバック学習

- [ ] 採用 / 却下データの蓄積分析
- [ ] Plugin 修正データの Style Profile 反映
- [ ] パーソナライズ精度の定量評価

### 6-3. Style Marketplace

- [ ] Style Profile 公開 / 販売
- [ ] 購入・評価・レビュー
- [ ] クリエイター収益分配
- [ ] ジャンル別ランキング

### 6-4. チーム・API

- [ ] チーム招待・権限管理（Studio プラン）
- [ ] 外部 API 公開
- [ ] Webhook 連携

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式ロードマップ初版 |
| 2026-06-04 | 1.0.0 | 6 フェーズ構成に改定 |
| 2026-06-06 | 2.0.0 | Phase 1-4 完了・Phase 5 コード完了を反映。残タスクを明確化 |
