# EditClone ロードマップ

バージョン: 1.0.0  
最終更新: 2026-06-04

---

## フェーズ概要

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | Web v1 安定化（デプロイ・MP4・制限・Analytics） | 🔄 進行中 |
| Phase 2 | Style Engine v1（Style Profile 生成・適用） | ⏳ 未着手 |
| Phase 3 | Project Sync Foundation | ⏳ 未着手 |
| Phase 4 | Rich Editing（テロップ・画像・ズーム・Premiere XML） | ⏳ 未着手 |
| Phase 5 | Plugin 早期着手（Phase 2〜3 と並行） | ⏳ 未着手 |
| Phase 6 | Learning & Marketplace | ⏳ 未着手 |

---

## Phase 1: Web v1 安定化（現在）

**目標:** 本番環境で安定稼働し、課金・制限・Analytics が機能する状態にする

### 1-1. 本番デプロイ（完了）

- [x] Railway バックエンドデプロイ（`https://editclone-backend-production.up.railway.app`）
- [x] Vercel フロントエンドデプロイ（`https://frontend-six-bice-51.vercel.app`）
- [x] Supabase Auth 連携（JWT 検証ミドルウェア）
- [x] Supabase Storage 連携（動画ファイル保存）
- [x] Stripe Checkout / Webhook / Portal
- [x] Stripe 商品・価格設定（Pro ¥980 / Creator ¥2,980 / Studio ¥9,800）

### 1-2. 残り必要な本番設定

- [ ] Railway に SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY / STRIPE_SECRET_KEY を設定
- [ ] Railway に STRIPE_WEBHOOK_SECRET を設定
- [ ] Vercel に NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY を設定
- [ ] Vercel に NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY を設定
- [ ] Supabase SQL Editor で `supabase/schema.sql` を実行
- [ ] Supabase Auth → Site URL を Vercel 本番 URL に更新

### 1-3. MP4 出力

- [ ] フロントエンド側 ffmpeg.wasm 統合（5分以下の動画）
- [ ] 長動画（5分超）用のサーバーレンダリング設計（Modal / Replicate）
- [ ] プランごとの最大時間制限エンフォース

### 1-4. 処理履歴・利用回数制限

- [ ] `usage_logs` テーブルへの月次カウント記録
- [ ] プランごとの上限チェック（Free: 3本、Pro: 30本、Creator: 100本）
- [ ] 制限超過時の適切なエラーレスポンスとフロントエンド表示

### 1-5. Analytics 基盤

- [ ] 動画処理イベントを Supabase ログに記録
- [ ] 月次 MRR 計算（Stripe Webhook から集計）
- [ ] ユーザー行動ログ（アップロード・処理完了・ダウンロード）

---

## Phase 2: Style Engine v1

**目標:** Style Profile を生成・保存・適用できる状態にする

### 2-1. Style Profile CRUD

- [ ] `style_profiles` テーブル設計・Supabase スキーマ追加
- [ ] Style Profile 作成 / 編集 / 削除 API
- [ ] フロントエンド Style Profile 管理 UI

### 2-2. 参考動画 URL 登録

- [ ] `reference_videos` テーブル設計
- [ ] URL 登録・メモ入力・Style Profile への紐づけ
- [ ] YouTube oEmbed によるタイトル・サムネイル取得
- [ ] **動画ダウンロードは行わない（永続禁止）**

### 2-3. 参考動画ファイル分析

- [ ] 参考動画ファイルのアップロード機能
- [ ] カットテンポ分析（平均カット間隔・リズム）
- [ ] 字幕密度分析
- [ ] 無音量・間の取り方分析
- [ ] 分析結果を Style Profile に反映

### 2-4. Style Profile 生成・適用

- [ ] 分析結果から Style Profile を自動生成
- [ ] 新規動画への Style Profile 適用
- [ ] LLM（Claude API）による編集方針生成
- [ ] 採用 / 却下 / 修正フィードバックの記録

---

## Phase 3: Project Sync Foundation

**目標:** Web と Plugin の同期基盤を設計・実装する

### 3-1. Project モデル定義

- [ ] `projects` テーブル設計・スキーマ追加
- [ ] `project_revisions` テーブル設計
- [ ] Project CRUD API

### 3-2. Export 履歴管理

- [ ] 出力形式・出力日時・バージョンの記録
- [ ] フロントエンド Project 管理 UI
- [ ] Sync Status 管理（draft / exported / modified_in_plugin / synced / conflict）

### 3-3. フィードバック記録

- [ ] `accepted_suggestions` / `rejected_suggestions` / `manual_adjustments` の記録 API
- [ ] フロントエンドでの採用 / 却下 UI

### 3-4. Sync API 設計

- [ ] Plugin 連携を想定した REST API 設計
- [ ] Conflict Handling 基本実装（Plugin 優先 / Web に通知）
- [ ] API 認証（Plugin → Web）

---

## Phase 4: Rich Editing

**目標:** 出力品質を大幅に向上させる

### 4-1. テロップ強化

- [ ] テロップスタイル（フォント・色・位置）の FCPXML 反映
- [ ] SRT 字幕のスタイル指定対応
- [ ] テロップ密度・位置の Style Profile 連動

### 4-2. 画像・写真対応

- [ ] 写真スライドショー動画化
- [ ] 動画内画像挿入
- [ ] ロゴ挿入
- [ ] ズーム / パン（ケン・バーンズエフェクト）

### 4-3. ズーム・演出

- [ ] ズームインポイントの自動提案
- [ ] B-roll 挿入タイミング提案
- [ ] トランジション提案

### 4-4. マルチ NLE 出力強化

- [ ] Premiere Pro XML 出力
- [ ] DaVinci Resolve XML / EDL 出力
- [ ] FCPXML の品質・互換性向上

---

## Phase 5: Plugin 早期着手（Phase 2〜3 と並行）

**目標:** 審査期間を見越して早期にコード開発・申請を開始する

Apple App Store 審査: 1〜3 ヶ月 / Adobe Marketplace 審査: 2〜4 週間  
**Phase 2 開始と同時に Plugin 設計を着手し、Phase 3 完了時点で申請する**

### 5-1. Premiere Plugin（UXP）

- [ ] Premiere UXP Plugin 設計（Panel UI + API 連携）
- [ ] EditClone アカウントログイン機能
- [ ] Style Profile 選択・適用機能
- [ ] Project 読み込み・タイムライン反映
- [ ] 修正内容の Sync API 送信
- [ ] Adobe Marketplace 申請

### 5-2. Final Cut Extension

- [ ] Workflow Extension 設計（Swift / SwiftUI）
- [ ] Apple Developer Program 登録・署名
- [ ] EditClone アカウントログイン機能
- [ ] Style Profile 選択・タイムライン反映
- [ ] Project Sync 連携
- [ ] Mac App Store 申請

### 5-3. DaVinci Resolve 連携

- [ ] DaVinci Resolve Script / Fusion Script 調査
- [ ] Panel 開発可能性調査
- [ ] MVP 連携方式確定

### 5-4. CapCut 連携調査

- [ ] CapCut API / SDK 調査
- [ ] 連携方式確定（Phase 6 以降）

---

## Phase 6: Learning & Marketplace

**目標:** AI 学習ループの完成と収益拡大

### 6-1. 編集前後ペア分析

- [ ] 編集前動画 + 編集後動画のペアアップロード
- [ ] カット位置・テロップ・演出の差分抽出
- [ ] Style Profile への自動反映
- [ ] 「編集 DNA」生成

### 6-2. ユーザーフィードバック学習

- [ ] 採用 / 却下データの蓄積分析
- [ ] Plugin 修正データの Style Profile 反映
- [ ] パーソナライズ精度向上

### 6-3. Style Marketplace

- [ ] Style Profile 公開 / 販売機能
- [ ] 購入・評価・レビュー
- [ ] クリエイター収益分配
- [ ] ジャンル別ランキング

### 6-4. チーム・API

- [ ] チーム招待・権限管理（Studio プラン）
- [ ] 外部 API 公開（Studio+ プラン）
- [ ] Webhook 連携

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式ロードマップ初版（MVP 時点） |
| 2026-06-04 | 1.0.0 | 6 フェーズ構成に全面改定。Style Engine・Project Sync・Plugin 並行着手・MP4・Analytics を追加 |
