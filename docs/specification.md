# EditClone 正式仕様書

バージョン: 1.0.0  
最終更新: 2026-06-04

---

## 1. プロダクト概要

EditClone は、動画素材を前提に、プロンプト・参考動画・編集前後ペア・過去編集履歴を使って、ユーザーの理想に近い編集を自動生成する **AI 編集エージェント**である。

- 素材なしで動画を生成する AI ではない
- ユーザーが持っている動画・画像・音声素材を高品質に編集する AI である
- 最終的には **Web アプリ** と **編集アプリ向け Plugin / Extension** の両方で提供する

| 項目 | 内容 |
|------|------|
| プロダクト名 | EditClone |
| リポジトリ | https://github.com/kentyon67/editclone |
| 想定ユーザー | YouTuber / TikToker / 動画編集者 / 企業 SNS 担当 / 動画編集フリーランス |
| 対象市場 | グローバル（日英対応） |
| 収益モデル | サブスクリプション（Free / Pro / Creator / Studio） |

---

## 2. コア価値

最大の強みは**「編集スタイルの学習・再現」**である。

単なる無音カット・字幕生成・動画変換ツールではない。  
ユーザーが使えば使うほど、以下を学習しパーソナライズされる。

- カットテンポ / 平均カット間隔
- テロップ量 / テロップ位置 / テロップ文字数 / フォントスタイル
- ズーム頻度 / ズーム強度
- 画像挿入傾向 / B-roll 頻度
- BGM / SE 傾向
- 色味 / 構成 / 間の取り方
- 参考動画との近さ
- ユーザーが採用・修正・却下した編集判断
- Plugin 上での手動修正
- Web 出力後に編集アプリ内で調整された内容

---

## 3. 入力

### 必須入力

- 元動画素材

### 任意入力

| カテゴリ | 具体的な入力 |
|---------|------------|
| 指示 | 編集プロンプト（テキスト） |
| 参考動画 | 参考動画ファイル / 参考動画 URL（YouTube / TikTok / Instagram Reels） |
| 学習素材 | 編集前動画 + 編集後動画（ペア） |
| 素材 | 画像 / ロゴ / BGM / 効果音 |
| ルール | 字幕ルール / ブランドガイドライン |
| 出力先 | 出力先編集アプリ（FCP / Premiere / DaVinci） |
| 既存ファイル | FCPXML / Premiere XML / DaVinci XML / EDL |

---

## 4. URL 参考動画ポリシー

URL 入力は UX 向上のため早期対応するが、**動画の無断ダウンロード・解析は行わない**。

### 初期対応（合法範囲）

- URL 保存・メモ入力
- YouTube oEmbed API によるタイトル・サムネイル取得のみ
- 参考動画としての Style Profile への紐づけ
- **解析対象はユーザーがアップロードした動画ファイルのみ**

### 禁止事項（永続）

- YouTube / TikTok / Instagram 等からの動画ダウンロード
- サードパーティ URL からの動画ストリーム解析
- ToS 違反コードの実装

### 将来対応（検討段階）

- ユーザーが権利を証明できる URL のみ解析
- YouTube oEmbed 範囲内でのスタイル分析補助
- 著作権・規約に完全準拠した設計のみ実装

---

## 5. 写真・画像素材の扱い

EditClone は動画だけでなく画像素材も扱う。

| 機能 | 説明 |
|------|------|
| スライド動画生成 | 写真をつなげたスライドショー動画化 |
| 画像挿入 | 動画内への画像・スクリーンショット・商品画像挿入 |
| ロゴ挿入 | ロゴオーバーレイ |
| ズーム / パン | 画像へのケン・バーンズエフェクト |
| 表示タイミング | 画像の表示タイミング提案 |
| テロップ連携 | 画像とテロップの組み合わせ提案 |

---

## 6. 出力形式（3 段階）

### 6-1. 完成動画 MP4 出力

| 項目 | 内容 |
|------|------|
| 対象ユーザー | すぐ投稿したい人 / 編集ソフト不要な人 / ショート動画制作者 |
| 特徴 | そのまま SNS 投稿可能 / UX が最もわかりやすい |
| 実装方式 | 短動画（〜5分）: ffmpeg.wasm（ブラウザ側）/ 長動画: Modal 等（サーバーレス従量課金） |
| 制限 | プランごとの最大時間制限あり（§14 参照） |

### 6-2. 編集プロジェクト出力

| 出力形式 | 対応アプリ | 状態 |
|---------|-----------|------|
| FCPXML | Final Cut Pro | 実装済み |
| Premiere XML | Adobe Premiere Pro | Phase 4 |
| DaVinci XML / EDL | DaVinci Resolve | Phase 4 |
| CapCut 連携 | CapCut | Phase 6 以降 |

### 6-3. Plugin / Extension 反映

編集アプリ内で EditClone にログインし、Web で作成した Style Profile や Project をタイムラインへ直接反映する。  
Plugin がなくても Web 単体で完全に動作する設計を維持する（§9 参照）。

---

## 7. Web アプリの役割

Web は EditClone の**作戦本部**である。Plugin なしで単体として高機能アプリとして成立する。

| 機能カテゴリ | 具体的な機能 |
|------------|------------|
| アカウント管理 | サインアップ / ログイン / プラン管理 |
| 素材管理 | 動画・画像・BGM アップロード / 参考動画 URL 登録 |
| 分析・生成 | 文字起こし / 無音検出 / カット提案 / Style Profile 生成 |
| 編集出力 | MP4 出力 / FCPXML 出力 / Premiere XML 出力 |
| スタイル管理 | Style Profile CRUD / 適用 / 共有 |
| プロジェクト管理 | Project 作成 / 履歴管理 / Sync 管理 |
| 課金 | Stripe Checkout / Billing Portal |
| Marketplace | Style Profile 販売・購入（Phase 6） |
| チーム管理 | チーム招待・権限管理（Studio プラン、Phase 5 以降） |

---

## 8. Plugin / Extension の役割

Plugin は**編集アプリ内の実行装置**である。

Web で作成した Project をさらに理想に近づける。  
Web からの出力ではない既存タイムラインにも Style Profile を適用できる。

| 機能 | 説明 |
|------|------|
| ログイン | 編集アプリ内で EditClone アカウントにログイン |
| Style Profile 呼び出し | Web で作成した Style Profile を選択・適用 |
| Project 読み込み | Web で作成した Project をタイムラインに反映 |
| タイムライン解析 | 既存タイムラインを解析して編集案を生成 |
| タイムライン反映 | カット・字幕・ズーム・マーカーを自動適用 |
| フィードバック同期 | ユーザーの修正内容を EditClone にフィードバック |
| Project Sync | 編集内容を Web と同期 |

### 対応 Plugin 実装順

1. Premiere Plugin（UXP）— Phase 5 並行着手
2. Final Cut Extension（Workflow Extension）— Phase 5 並行着手
3. DaVinci Resolve Script / Panel — Phase 5
4. CapCut 連携 — Phase 6 以降

**Plugin 開発は Phase 2〜3 と並行して早期着手する。**  
Apple / Adobe の審査（各 1〜3 ヶ月）を考慮し、コード完成後すぐ申請できるよう先行着手。

---

## 9. Web 単体での完全動作原則

- Plugin がなくてもすべての基本機能が Web で利用できる
- Plugin は「さらに理想に近づける」ための拡張であり、必須要件ではない
- Plugin 専用機能（タイムライン直接反映・リアルタイム同期）は Plugin 限定とするが、同等の価値は Web の出力ファイル + 手動インポートで代替できる

---

## 10. EditClone Account / Project Sync

EditClone は Web と Plugin で**同じアカウント**を共有する。

### クラウドに保存する情報

- Style Profile / Project / 素材 / 参考動画 URL
- 編集プロンプト / 出力履歴 / Plugin 修正履歴
- 採用・却下された編集提案 / 学習履歴

### Project Sync の目的

```
1. Web で編集案を生成
2. FCPXML / Premiere XML 等で出力
3. Plugin で Project を開く
4. 編集アプリ内で微調整
5. 修正内容を EditClone へ同期
6. Style Profile が改善
7. 次回生成精度が向上  ←ループ
```

### Project Sync で管理する情報

| フィールド | 説明 |
|-----------|------|
| project_id / user_id / project_name | 識別情報 |
| source_video_ids | 元動画 |
| style_profile_id | 適用スタイル |
| export_format / exported_to | 出力先 |
| export_version / latest_revision_id | バージョン管理 |
| web_modified_at / plugin_modified_at | 更新タイムスタンプ |
| sync_status | 同期状態（下記参照） |
| accepted_suggestions / rejected_suggestions / manual_adjustments | フィードバック |
| plugin_app / plugin_project_reference | Plugin 識別 |

### Sync Status

| 状態 | 説明 |
|------|------|
| draft | 下書き |
| processing | 処理中 |
| exported | 出力済み |
| opened_in_plugin | Plugin で開かれた |
| modified_in_plugin | Plugin で変更あり |
| synced | Web と同期済み |
| conflict | 競合発生 |
| archived | アーカイブ |

### Conflict Handling

Web と Plugin で同時に変更が発生した場合は**勝手に上書きしない**。

- 初期: Plugin 側の変更を優先 / Web には「Plugin で変更あり」と表示 / 手動選択
- 将来: 差分比較 / バージョン履歴 / ロールバック / 共同編集

---

## 11. Style Profile

Style Profile は編集スタイルを数値化・保存・再利用するための**中核データ**である。

### 保存項目

| カテゴリ | フィールド |
|---------|-----------|
| 基本情報 | style_name / target_platform / genre |
| カット | cut_speed / average_cut_interval / silence_tolerance |
| テロップ | caption_density / caption_position / caption_max_chars / caption_font_style / caption_color |
| 演出 | zoom_frequency / zoom_strength / image_insert_frequency / b_roll_frequency |
| 音声 | se_density / bgm_energy |
| 映像 | color_tone / transition_style |
| 構成 | hook_style / pacing_style / ending_style |
| 参考情報 | reference_urls |
| 学習状態 | training_video_count / accepted_edit_count / rejected_edit_count / manual_adjustment_count / plugin_feedback_count / user_feedback_notes |

---

## 12. 学習・パーソナライズ

### 初期段階

- ルールベース + 統計分析
- LLM による編集方針生成（Claude API）
- Style Profile 保存・更新
- ユーザーの採用 / 却下 / 修正フィードバック反映
- Plugin 修正履歴反映
- Project Sync による編集履歴蓄積

### 将来

- 編集前後ペアデータを蓄積して傾向学習
- ユーザーごとの Style Model 作成
- Marketplace で販売可能な編集スタイルモデルを生成

---

## 13. 編集前後ペア学習

将来的に最重要機能として実装する。

| 項目 | 内容 |
|------|------|
| 入力 | 編集前動画 + 編集後動画 |
| 分析対象 | カット位置 / 削除区間 / テロップ挿入 / 画像挿入 / ズーム / BGM・SE / 構成変化 / 間の取り方 |
| 出力 | Style Profile 更新 / 新規動画へのスタイル適用 / 編集者ごとの「編集 DNA」生成 |

---

## 14. 収益モデル

透かし（ウォーターマーク）なし。制限は**量的制限のみ**。

| プラン | 月額 | 本数 | 最大時間 | Style Profile | Plugin | Project Sync |
|--------|------|------|---------|--------------|--------|-------------|
| Free | 無料 | 3本 | 3分 | 1個 | 不可 | 不可 |
| Pro | ¥980 | 30本 | 15分 | 5個 | 不可 | 不可 |
| Creator | ¥2,980 | 100本 | 60分 | 20個 | 可 | 可 |
| Studio | ¥9,800 | 無制限 | 無制限 | 無制限 | 可（複数） | 可 |

Studio プランの追加特典: チーム利用 / API アクセス / Marketplace 販売機能

---

## 15. Marketplace（将来）

Style Profile を販売・共有できるプラットフォーム。

| 機能 | 説明 |
|------|------|
| 販売・購入 | Style Profile を Marketplace で公開・購入 |
| レビュー | 評価・レビュー機能 |
| 収益分配 | クリエイターへの収益還元 |
| 検索 | ジャンル別・人気順ランキング |
| チーム共有 | Studio プランでのチーム内共有 |

---

## 16. 現在実装済み機能（Phase 1 完了分）

| 機能 | エンドポイント / ファイル |
|------|----------------------|
| ヘルスチェック | GET /health |
| 動画アップロード | POST /videos/upload |
| 動画基本情報 | GET /videos/info/{id} |
| Whisper 文字起こし | POST /videos/transcribe/{id} |
| 無音検出 | POST /videos/detect-silence/{id} |
| カット提案 | POST /videos/suggest-cuts/{id} |
| FCPXML + ZIP 生成 | POST /videos/generate-fcpxml/{id} |
| YouTube チャプター | POST /videos/chapters/{id} |
| SRT 字幕 | POST /videos/export-srt/{id} |
| 非同期ジョブ処理 | POST /videos/process/{id} |
| ジョブ管理 | GET /jobs/{id} / GET /jobs/{id}/download |
| Stripe Checkout | POST /billing/create-checkout |
| Stripe Webhook | POST /billing/webhook |
| Stripe Portal | GET /billing/portal |
| Next.js フロントエンド | frontend/ |
| Supabase Auth | app/middleware/auth.py |
| Supabase Storage | app/services/storage.py |

---

## 17. 非機能要件

| 要件 | 内容 |
|------|------|
| 非同期処理 | 長時間処理は非同期ジョブ化（BackgroundTasks / 将来: Celery） |
| ストレージ | 動画はクラウドストレージ（Supabase Storage）へ保存 |
| 進捗表示 | 処理進捗をフロントエンドでリアルタイム表示 |
| MP4 レンダリング | 短動画: ffmpeg.wasm（ブラウザ）/ 長動画: Modal / Replicate（サーバーレス） |
| 利用量制限 | プランごとの本数・時間制限を本番環境で強制 |
| Secret 管理 | API キー・Secret は .env 管理 / コードにハードコード禁止 |
| URL 動画 | 違法ダウンロード禁止 / oEmbed 範囲のみ合法 |
| Plugin 設計 | Plugin は Web API と連携する設計 / Web 単体でも全機能動作 |
| Project Sync | 競合時は勝手な上書きをしない |
| 学習データ | 編集履歴を Style Profile 改善に利用できる形で保存 |
| 著作権 | 参考動画の著作権・プラットフォーム規約に完全準拠 |
| スケーラビリティ | 大容量動画対応を想定した設計 |
| Analytics | ユーザー行動・MRR・チャーン計測を Phase 1 から実装 |

---

## 18. 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式仕様書初版（MVP 時点） |
| 2026-06-04 | 1.0.0 | プロダクト要件正式再定義。マルチ NLE 対応・Style Profile・Project Sync・Plugin 設計・3 段階出力を追加 |
