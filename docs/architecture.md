# EditClone アーキテクチャ設計書

バージョン: 1.0.0  
最終更新: 2026-06-04

---

## 1. 現在の構成（Phase 1 完了状態）

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
        ├── Supabase PostgreSQL（ユーザー・ジョブ・課金 DB）
        └── Stripe（Checkout / Webhook / Portal）
```

### 技術スタック

| 区分 | 技術 | 役割 |
|------|------|------|
| Backend | Python 3.11 / FastAPI / Uvicorn | API サーバー |
| 動画処理 | ffmpeg / OpenCV | 無音検出・動画情報取得 |
| AI（文字起こし） | faster-whisper（CTranslate2） | ローカル Whisper 推論 |
| AI（将来） | Claude API | 編集方針生成・Style Profile 分析 |
| 出力 | FCPXML / SRT / ZIP | 編集ソフト向けファイル |
| Frontend | Next.js 16 / React 19 / Tailwind CSS v4 | Web アプリ |
| i18n | next-intl 4.x（ja / en） | 多言語対応 |
| 認証 | Supabase Auth（JWT） | ユーザー認証 |
| DB | Supabase PostgreSQL | データ永続化 |
| ストレージ | Supabase Storage | 動画・素材ファイル |
| 課金 | Stripe Checkout + Webhook | サブスクリプション管理 |
| ホスティング | Railway（Backend）/ Vercel（Frontend） | 本番インフラ |

---

## 2. ディレクトリ構成（現在）

```
editclone/
├── app/
│   ├── main.py                   # FastAPI エントリポイント (v0.3.0)
│   ├── middleware/
│   │   └── auth.py               # Supabase JWT 認証ミドルウェア
│   ├── routers/
│   │   ├── videos.py             # 動画処理エンドポイント
│   │   ├── jobs.py               # 非同期ジョブ管理
│   │   └── billing.py            # Stripe 課金
│   └── services/
│       ├── video_info.py         # OpenCV による動画情報取得
│       ├── transcription.py      # faster-whisper 文字起こし
│       ├── silence.py            # ffmpeg 無音検出
│       ├── cut_suggestion.py     # カット提案ロジック
│       ├── fcpxml.py             # FCPXML 生成
│       ├── chapters.py           # YouTube チャプター生成
│       ├── srt.py                # SRT 字幕生成
│       ├── jobs.py               # 非同期ジョブ処理
│       └── storage.py            # Supabase Storage / ローカルフォールバック
├── frontend/
│   ├── app/[locale]/             # Next.js App Router（ja / en）
│   │   ├── page.tsx              # ランディングページ
│   │   ├── login/page.tsx        # ログイン
│   │   ├── signup/page.tsx       # サインアップ
│   │   ├── dashboard/page.tsx    # ダッシュボード
│   │   ├── upload/page.tsx       # アップロード
│   │   ├── results/[jobId]/      # 処理結果
│   │   ├── pricing/page.tsx      # 料金プラン（Stripe 連携）
│   │   └── account/page.tsx      # アカウント管理
│   ├── lib/
│   │   ├── api.ts                # バックエンド API クライアント
│   │   └── supabase.ts           # Supabase ブラウザクライアント
│   ├── i18n/
│   │   ├── routing.ts            # next-intl ルーティング設定
│   │   └── request.ts            # ロケール別メッセージ読み込み
│   ├── messages/
│   │   ├── ja.json               # 日本語翻訳
│   │   └── en.json               # 英語翻訳
│   └── middleware.ts             # 認証保護ルート + i18n
├── supabase/
│   └── schema.sql                # DB スキーマ（profiles / usage_logs / jobs）
├── docs/
│   ├── specification.md
│   ├── roadmap.md
│   ├── architecture.md
│   └── deploy-guide.md
├── Dockerfile.backend            # python:3.11 + ffmpeg + libgomp1
├── railway.json                  # Railway デプロイ設定
├── frontend/vercel.json          # Vercel デプロイ設定
└── CLAUDE.md                     # 開発ルール
```

---

## 3. データフロー（現在）

### 動画処理フロー

```
POST /videos/upload
  └── Supabase Storage または uploads/ に保存
  └── video_id を返す

POST /videos/process/{video_id}
  └── BackgroundTask として非同期ジョブ作成
  └── job_id を即座に返す

  [バックグラウンド処理]
  1. extract_video_info（OpenCV）
  2. transcribe_video（faster-whisper）
  3. suggest_cuts（無音検出 + カット提案）
  4. generate_chapters（YouTube チャプター）
  5. generate_srt（SRT 字幕）
  6. build_fcpxml（FCPXML 生成）
  7. ZIP 化（FCPXML + 動画ファイル）→ job.result["zip_bytes"]

GET /jobs/{job_id}          # ポーリング（フロントが 2 秒ごとに確認）
GET /jobs/{job_id}/download  # ZIP ダウンロード
```

### 認証フロー

```
フロントエンド（Supabase Auth）
  └── supabase.auth.signIn → access_token 取得
  └── API 呼び出し時 Authorization: Bearer {token} を付与

バックエンド（auth.py）
  └── AUTH_ENABLED = True（本番）→ supabase.auth.get_user(token) で検証
  └── AUTH_ENABLED = False（ローカル開発）→ ダミーユーザーを返す
```

---

## 4. DB スキーマ（現在）

```sql
-- ユーザープロファイル（Supabase Auth と連携）
profiles (
  id uuid PRIMARY KEY REFERENCES auth.users,
  email text,
  plan text DEFAULT 'free',      -- free / pro / creator / studio
  stripe_customer_id text,
  stripe_subscription_id text,
  subscription_status text
)

-- 月次利用量
usage_logs (
  user_id uuid REFERENCES profiles,
  year_month text,               -- 例: '2026-06'
  video_count integer DEFAULT 0,
  UNIQUE(user_id, year_month)
)

-- ジョブ管理
jobs (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES profiles,
  video_id text,
  video_filename text,
  status text,                   -- pending / processing / completed / failed
  noise_db float,
  min_duration float,
  error_message text
)
```

---

## 5. MP4 レンダリング設計（Phase 1 追加）

```
短動画（〜5分）
  └── ffmpeg.wasm（WebAssembly）
  └── ブラウザ側でレンダリング
  └── サーバーコスト $0

長動画（5分超）
  └── Modal / Replicate（サーバーレス従量課金）
  └── コスト: $0.30〜0.80 / 30分動画
  └── 非同期ジョブとして処理
```

| プラン | MP4 最大時間 | レンダリング方式 |
|--------|------------|----------------|
| Free | 3分 | ffmpeg.wasm |
| Pro | 15分 | ffmpeg.wasm |
| Creator | 60分 | ffmpeg.wasm + Modal |
| Studio | 無制限 | Modal |

---

## 6. Phase 2〜3 で追加するDB スキーマ

```sql
-- Style Profile（Phase 2）
style_profiles (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES profiles,
  style_name text,
  target_platform text,
  genre text,
  cut_speed text,
  average_cut_interval float,
  silence_tolerance float,
  caption_density text,
  caption_position text,
  caption_max_chars int,
  caption_font_style text,
  caption_color text,
  zoom_frequency text,
  zoom_strength float,
  image_insert_frequency text,
  b_roll_frequency text,
  se_density text,
  bgm_energy text,
  color_tone text,
  transition_style text,
  hook_style text,
  pacing_style text,
  ending_style text,
  reference_urls text[],
  training_video_count int DEFAULT 0,
  accepted_edit_count int DEFAULT 0,
  rejected_edit_count int DEFAULT 0,
  manual_adjustment_count int DEFAULT 0,
  plugin_feedback_count int DEFAULT 0,
  user_feedback_notes text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
)

-- 参考動画 URL 登録（Phase 2）
reference_videos (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES profiles,
  style_profile_id uuid REFERENCES style_profiles,
  url text,
  platform text,             -- youtube / tiktok / instagram / other
  title text,                -- oEmbed 取得
  thumbnail_url text,        -- oEmbed 取得
  notes text,
  created_at timestamptz DEFAULT now()
)

-- Project（Phase 3）
projects (
  id uuid PRIMARY KEY,
  user_id uuid REFERENCES profiles,
  project_name text,
  source_video_ids text[],
  style_profile_id uuid REFERENCES style_profiles,
  export_format text,        -- fcpxml / premiere_xml / davinci_xml / mp4
  exported_to text,          -- fcp / premiere / davinci
  export_version int DEFAULT 0,
  sync_status text DEFAULT 'draft',
  web_modified_at timestamptz,
  plugin_modified_at timestamptz,
  plugin_app text,
  plugin_project_reference text,
  created_at timestamptz DEFAULT now()
)

-- Project リビジョン（Phase 3）
project_revisions (
  id uuid PRIMARY KEY,
  project_id uuid REFERENCES projects,
  revision_number int,
  accepted_suggestions jsonb,
  rejected_suggestions jsonb,
  manual_adjustments jsonb,
  source text,               -- web / plugin
  created_at timestamptz DEFAULT now()
)
```

---

## 7. Plugin / Extension アーキテクチャ（Phase 5）

```
[Plugin（Premiere UXP / FCP Extension / DaVinci Panel）]
        │ HTTPS
        ▼
[FastAPI Plugin API]  /api/v1/plugin/...
        │
        ├── Supabase Auth（Plugin からの JWT 検証）
        ├── Style Profile API（GET / SELECT）
        ├── Project Sync API（GET / PATCH / POST revision）
        └── Feedback API（採用 / 却下 / 修正の記録）
```

### Plugin ↔ Web 同期フロー

```
Web 側
  1. 動画処理 → Project 作成（sync_status: draft）
  2. FCPXML / Premiere XML 出力（sync_status: exported）

Plugin 側
  3. Plugin が Project を開く（sync_status: opened_in_plugin）
  4. タイムライン調整（sync_status: modified_in_plugin）
  5. Sync API で修正内容を送信（sync_status: synced）

Web 側
  6. 修正内容を受信 → Style Profile 更新
  7. 次回処理の精度向上
```

### Conflict Handling

```
Web と Plugin が競合した場合:
  初期: Plugin 優先 / Web に「Plugin で変更あり」バッジ表示
  将来: 差分表示 UI → ユーザーが手動選択
```

---

## 8. Style Profile 学習ループ

```
[元動画 + プロンプト + Style Profile]
        ↓ 処理
[AI 編集案（カット・テロップ・ズーム等）]
        ↓ 出力
[FCPXML / MP4 / Premiere XML]
        ↓ Plugin or 手動インポート
[編集アプリでの調整]
        ↓ フィードバック（採用 / 却下 / 修正）
[Style Profile 更新]
        ↓
[次回処理の精度向上]  ←ループ
```

---

## 9. FCPXML 仕様

- バージョン: FCPXML v1.10
- 時間フォーマット: `{ms}/1000s`（ラショナル文字列）
- メディアパス: `file://localhost/EDITCLONE_MEDIA/{filename}`（プレースホルダー）
- ZIP 構造: `{video_id}_editclone.zip` → `{video_id}.fcpxml` + `media/{filename}`
- FCP でのリンク修正: File > Relink Media で 1 クリック再リンク

---

## 10. ローカル開発環境

```powershell
# バックエンド
cd C:\Projects\editclone
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000/docs

# フロントエンド（別ターミナル）
cd frontend
npm install --strict-ssl=false
npm run dev
# → http://localhost:3000/ja
```

ローカルでは Supabase / Stripe 未設定でも動作する（フォールバック機能あり）:
- `AUTH_ENABLED = False` → ダミーユーザーで認証スキップ
- `USE_CLOUD = False` → ローカルの `uploads/` ディレクトリを使用

---

## 11. 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2026-06-03 | 0.1.0 | 正式アーキテクチャ設計書初版（MVP 時点） |
| 2026-06-04 | 1.0.0 | 現在の実装状態に全面更新。MP4・Plugin・Style Profile・Project Sync・DB スキーマを追加 |
