# EditClone アーキテクチャ設計書

バージョン: 2.0.0  
最終更新: 2026-06-06

---

## 1. 現在の構成（Phase 1〜4 実装済み）

```
[ユーザー（ブラウザ）]
        │ HTTPS
        ▼
[Next.js 16 フロントエンド]
[Vercel / Edge Network]
        │ HTTPS
        ▼
[FastAPI バックエンド]
[Railway / Docker / python:3.11]
        │
        ├── Supabase Auth（JWT 検証）
        ├── Supabase Storage（動画・素材ファイル）
        ├── Supabase PostgreSQL（DB）
        └── Stripe（Checkout / Webhook / Portal）

[Plugin]
  fcp-extension/    — macOS Swift/SwiftUI WKWebView
  premiere-cep/     — CEP Panel (HTML/JS + ExtendScript)
  davinci-script/   — Python スクリプト（Fusion Scripts）
  fcp/              — 基本 FCP 連携
  premiere/         — Premiere 基本連携
  davinci/          — DaVinci 基本連携
```

### 技術スタック

| 区分 | 技術 | 役割 |
|------|------|------|
| Backend | Python 3.11 / FastAPI / Uvicorn | API サーバー |
| 動画処理 | ffmpeg / OpenCV | 無音検出・カット・MP4レンダリング |
| AI（文字起こし） | faster-whisper（CTranslate2） | ローカル Whisper 推論 |
| AI（編集指示） | Claude API（claude-sonnet-4-6） | セマンティックカット・Style Profile改善 |
| 出力 | FCPXML / Premiere XML / EDL / SRT / MP4 | 各 NLE + 完成動画 |
| Frontend | Next.js 16 / React 19 / Tailwind CSS v4 | Web アプリ |
| i18n | next-intl 4.x（ja / en） | 多言語対応 |
| 認証 | Supabase Auth（JWT） | ユーザー認証 |
| DB | Supabase PostgreSQL | データ永続化 |
| ストレージ | Supabase Storage | 動画・素材・成果物 |
| 課金 | Stripe Checkout + Webhook | サブスクリプション管理 |
| ホスティング | Railway（Backend）/ Vercel（Frontend） | 本番インフラ |

---

## 2. ディレクトリ構成（現在）

```
editclone/
├── app/
│   ├── main.py
│   ├── middleware/
│   │   └── auth.py               # Supabase JWT 認証
│   ├── routers/
│   │   ├── videos.py             # 動画処理エンドポイント
│   │   ├── jobs.py               # 非同期ジョブ管理
│   │   ├── billing.py            # Stripe 課金
│   │   ├── style_profiles.py     # Style Profile CRUD
│   │   ├── projects.py           # Project Sync
│   │   ├── plugin.py             # Plugin API（認証付き）
│   │   └── usage.py              # 利用量管理
│   └── services/
│       ├── video_info.py         # OpenCV 動画情報
│       ├── transcription.py      # faster-whisper 文字起こし
│       ├── silence.py            # ffmpeg silencedetect
│       ├── cut_suggestion.py     # 無音カット提案
│       ├── ai_edit.py            # Claude API セマンティックカット
│       ├── fcpxml.py             # FCPXML（字幕 caption lane + NTSC DF）
│       ├── premiere_xml.py       # Premiere XML（XMEML + NTSC DF）
│       ├── edl.py                # EDL（DaVinci 用 + NTSC DF）
│       ├── chapters.py           # YouTube チャプター
│       ├── srt.py                # SRT 字幕
│       ├── mp4_render.py         # ffmpeg MP4 レンダリング + 字幕焼き込み
│       ├── style_profiles.py     # Style Profile CRUD + AI refinement
│       ├── projects.py           # Project Sync + Revision 管理
│       ├── jobs.py               # 非同期ジョブ処理（全パイプライン）
│       ├── storage.py            # Supabase Storage / ローカルフォールバック
│       ├── usage.py              # プランごとの利用制限チェック
│       └── analytics.py          # Supabase ログ（処理イベント）
├── frontend/
│   ├── app/[locale]/
│   │   ├── page.tsx              # ランディングページ
│   │   ├── login/                # ログイン
│   │   ├── signup/               # サインアップ
│   │   ├── dashboard/            # ダッシュボード + 処理履歴
│   │   ├── upload/               # アップロード + Style Profile バッジ
│   │   ├── results/[jobId]/      # 処理結果 + インライン MP4 プレーヤー
│   │   ├── styles/               # Style Profile 管理（Caption Style UI）
│   │   ├── projects/[id]/        # Project 詳細 + 再エクスポート
│   │   ├── pricing/              # 料金プラン（Stripe 連携）
│   │   └── account/              # アカウント + Plugin トークン
│   ├── lib/
│   │   ├── api.ts                # バックエンド API クライアント
│   │   └── supabase.ts           # Supabase ブラウザクライアント
│   └── messages/
│       ├── ja.json               # 日本語翻訳
│       └── en.json               # 英語翻訳
├── plugins/
│   ├── fcp-extension/            # macOS Swift/SwiftUI Workflow Extension
│   ├── fcp/                      # FCP 基本連携
│   ├── premiere-cep/             # Premiere CEP Panel（HTML/JS）
│   ├── premiere/                 # Premiere 基本連携
│   ├── davinci-script/           # DaVinci Python スクリプト
│   └── davinci/                  # DaVinci 基本連携
├── supabase/
│   └── schema.sql                # DB スキーマ v5（idempotent）
├── docs/
├── Dockerfile.backend
├── railway.json
└── frontend/vercel.json
```

---

## 3. ジョブ処理パイプライン（現在）

```
POST /videos/upload
  └── Supabase Storage または uploads/ に保存
  └── video_id を返す

POST /videos/process/{video_id}
  └── BackgroundTask で非同期ジョブ作成
  └── job_id を即座に返す

  [バックグラウンド処理]
  1. extract_video_info（OpenCV）
  2. transcribe_video（faster-whisper）
  3. suggest_cuts（ffmpeg silencedetect）
  4. analyze_transcript_for_cuts（Claude API）← prompt がある場合のみ
  5. merge_cuts（無音 + AI カットを統合）
  6. generate_chapters（YouTube チャプター）
  7. generate_srt（SRT 字幕）
  8. build_fcpxml（FCPXML 字幕 caption lane + NTSC DF タイムコード）
  9. build_premiere_xml（XMEML + NTSC DF タイムコード）
  10. build_edl（DaVinci EDL + NTSC DF タイムコード）
  11. render_mp4（ffmpeg filter_complex trim+concat）
  12. add_subtitles_to_mp4（ASS style 焼き込み + Style Profile 反映）
  13. ZIP 化（fcp/ + premiere/ + davinci/ + subtitles/ + media/ + chapters.txt）
  14. Supabase Storage へ ZIP・MP4 アップロード
  15. Project + Revision 自動作成（Phase 3）

GET /jobs/{job_id}          # ポーリング（2秒ごと）
GET /jobs/{job_id}/download  # ZIP ダウンロード
```

---

## 4. DB スキーマ（現在 v5）

```sql
-- ユーザープロファイル
profiles (
  id uuid PRIMARY KEY REFERENCES auth.users,
  email text, plan text DEFAULT 'free',
  stripe_customer_id text, stripe_subscription_id text,
  subscription_status text
)

-- 月次利用量
usage_logs (
  user_id uuid, year_month text, video_count integer,
  UNIQUE(user_id, year_month)
)

-- ジョブ管理（Supabase 永続化）
jobs (
  id uuid PRIMARY KEY, user_id uuid, video_id text,
  video_filename text, status text,
  noise_db float, min_duration float, prompt text,
  result_zip_path text, result_mp4_path text,
  result_metadata jsonb, error_message text,
  created_at timestamptz, completed_at timestamptz
)

-- Style Profile（Phase 2）
style_profiles (
  id uuid PRIMARY KEY, user_id uuid,
  name text, description text, is_active boolean,
  noise_db float, min_silence_seconds float,
  default_prompt text, ai_prompt text,
  caption_style jsonb,    -- {font_size, position, primary_color, outline_color, bold}
  accepted_count integer, rejected_count integer,
  partial_count integer, job_count integer,
  reference_videos jsonb, feedback_history jsonb,
  created_at timestamptz, updated_at timestamptz
)

-- Project（Phase 3）
projects (
  id uuid PRIMARY KEY, user_id uuid,
  name text, source_job_id uuid,
  style_profile_id uuid,
  sync_status text DEFAULT 'exported',
  created_at timestamptz, updated_at timestamptz
)

-- Project リビジョン（Phase 3）
project_revisions (
  id uuid PRIMARY KEY, project_id uuid, user_id uuid,
  revision_number integer, source text,
  metadata jsonb, conflict_with uuid,
  created_at timestamptz
)
```

---

## 5. MP4 レンダリング詳細

```
render_mp4（mp4_render.py）
  ├── カットなし → -c copy でストリームコピー（高速・劣化なし）
  └── カットあり → filter_complex:
        [0:v]trim=start=S:end=E,setpts=PTS-STARTPTS[v0]
        [0:a]atrim=start=S:end=E,asetpts=PTS-STARTPTS[a0]
        ...
        [v0][a0][v1][a1]...concat=n=N:v=1:a=1[outv][outa]
        → libx264 CRF=18, preset=fast, AAC 128k, faststart

add_subtitles_to_mp4
  ├── SRT → tempfile → subtitles filter + force_style（ASS パラメータ）
  ├── ASS color: #RRGGBB → &H00BBGGRR（リトルエンディアン BGR）
  ├── フォント: Noto Sans CJK JP（Railway コンテナに fonts-noto-cjk インストール済み）
  └── Style Profile.caption_style から font_size / position / color / bold を取得
```

---

## 6. Plugin アーキテクチャ

### FCP Extension（fcp-extension/）

```
[macOS Swift/SwiftUI Workflow Extension]
  EditCloneWebView.swift
    └── WKWebView で frontend をロード
    └── window.editcloneBridge = true / window.editcloneNLE = 'fcp' を inject
    └── JS → Swift メッセージハンドラ "editclone"
          └── action: "importFCPXML"
                └── GET /plugin/jobs/{jobId}/fcpxml（Bearer トークン）
                └── .fcpxml を temp に保存
                └── NSWorkspace.shared.open(url) で FCP が直接開く
```

### Premiere CEP（premiere-cep/）

```
[CEP Panel（HTML/JS）]
  main.js
    └── iframe で frontend の /dashboard?nle=premiere をロード
    └── postMessage で action: "importPremiereXML" を受信
          └── GET /plugin/jobs/{jobId}/premiere-xml（Bearer トークン）
          └── XML を temp に保存
          └── evalScript → ExtendScript で Premiere にインポート
```

### DaVinci Script（davinci-script/）

```
[Python スクリプト（Fusion Scripts / Utility）]
  editclone_import.py
    └── GET /plugin/jobs（Bearer トークン）→ 完了ジョブ一覧
    └── 選択したジョブの ZIP をダウンロード
    └── ZIP 展開 → FCPXML + media + SRT
    └── DaVinciResolveScript API でメディアプールへインポート
    └── FCPXML からタイムライン自動生成
```

---

## 7. Style Profile 学習ループ

```
[アップロード + プロンプト + Style Profile]
        ↓ 処理
[Whisper 文字起こし + 無音検出 + Claude AI カット]
        ↓ 出力
[MP4（字幕焼き込み）+ ZIP（FCPXML/Premiere XML/EDL/SRT）]
        ↓ Plugin でインポート or 手動
[編集アプリでの微調整]
        ↓ フィードバック（accept/partial/reject）
[Style Profile 更新 + AI 改善提案（Claude API）]
        ↓
[次回処理の精度向上]  ←ループ
```

---

## 8. Project Sync フロー

```
Web 動画処理完了
  → Project 自動作成（sync_status: exported）
  → Revision #1 記録（source: web, cut_count, prompt 等）

Plugin でインポート
  → POST /projects/{id}/revisions（source: plugin）
  → 競合検出（web_revision と plugin_revision のタイムスタンプ比較）
  → conflict なら sync_status: conflict

競合解決
  → ユーザーが Web でどちらを採用か選択
  → sync_status: synced
```

---

## 9. ローカル開発環境

```powershell
# バックエンド
cd C:\Projects\editclone
.venv\Scripts\activate
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# フロントエンド
cd frontend
npm run dev
# → http://localhost:3000/ja
```

ローカルでは未設定でも動作:
- `AUTH_ENABLED = False` → ダミーユーザーで認証スキップ
- `USE_CLOUD = False` → ローカルの `uploads/` を使用

---

## 10. 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式アーキテクチャ初版 |
| 2026-06-04 | 1.0.0 | MP4・Plugin・Style Profile・Project Sync 追加 |
| 2026-06-06 | 2.0.0 | 実装済み全機能を反映。Phase 2-4 完了・Plugin コード完了状態に更新 |
