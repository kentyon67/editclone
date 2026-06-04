# EditClone デプロイガイド

このガイドに従って順番に設定してください。

---

## 1. Supabase 設定

### 1-1. プロジェクト情報の取得

[Supabase Dashboard](https://supabase.com/dashboard) → プロジェクトを選択

**Settings → API** から以下をコピー:
- `Project URL` → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
- `anon / public` キー → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `service_role` キー → `SUPABASE_SERVICE_ROLE_KEY`（絶対に公開しない）

### 1-2. DBスキーマを適用

**SQL Editor** を開き、`supabase/schema.sql` の内容を貼り付けて実行。

### 1-3. 認証設定

**Authentication → Settings → Email**:
- `Enable Email Confirmations`: ON（本番）または OFF（テスト）
- `Site URL`: `https://your-app.vercel.app`

### 1-4. Storageバケット確認

**Storage** メニューで `videos` バケットが作成されているか確認。
なければ: New bucket → 名前 `videos` → Public: OFF → 作成。

---

## 2. Stripe 設定

### 2-1. APIキーの取得

[Stripe Dashboard](https://dashboard.stripe.com) → **Developers → API keys**:
- `Publishable key` → `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`
- `Secret key` → `STRIPE_SECRET_KEY`

### 2-2. 商品・価格の作成

**Products → Add product** で3つ作成:

| 商品名 | 価格 | 請求サイクル | 対応変数 |
|--------|------|-------------|---------|
| EditClone Pro | ¥980 | 月次 | `STRIPE_PRICE_PRO` |
| EditClone Creator | ¥2,980 | 月次 | `STRIPE_PRICE_CREATOR` |
| EditClone Studio | ¥9,800 | 月次 | `STRIPE_PRICE_STUDIO` |

各商品作成後に表示される **Price ID** (`price_xxxxx`) を環境変数にセット。

### 2-3. Webhookの設定

**Developers → Webhooks → Add endpoint**:
- URL: `https://your-railway-app.up.railway.app/billing/webhook`
- イベント:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`

作成後、**Signing secret** → `STRIPE_WEBHOOK_SECRET`

---

## 3. Railway（バックエンド）設定

### 3-1. デプロイ手順

1. [Railway Dashboard](https://railway.app) → **New Project**
2. **Deploy from GitHub repo** → `kentyon67/editclone` を選択
3. **Root Directory**: `/`（ルート）
4. Railwayが `railway.json` を検出して自動設定

### 3-2. 環境変数の設定

Railway Dashboard → プロジェクト → **Variables** タブ:

```
CORS_ORIGINS=https://your-app.vercel.app
WHISPER_MODEL=base
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_CREATOR=price_...
STRIPE_PRICE_STUDIO=price_...
```

### 3-3. ドメインを確認

設定後に表示される Railway の URL（例: `https://editclone-production.up.railway.app`）をメモ。

---

## 4. Vercel（フロントエンド）設定

### 4-1. デプロイ手順

1. [Vercel Dashboard](https://vercel.com) → **New Project**
2. **Import Git Repository** → `kentyon67/editclone`
3. **Root Directory**: `frontend`（重要）
4. **Framework Preset**: Next.js（自動検出）

### 4-2. 環境変数の設定

Vercel Dashboard → プロジェクト → **Settings → Environment Variables**:

```
NEXT_PUBLIC_API_URL=https://editclone-production.up.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...（公開キー）
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

### 4-3. SupabaseのSite URLを更新

Supabase → **Authentication → Settings**:
- `Site URL`: Vercelの本番URL（例: `https://editclone.vercel.app`）
- `Redirect URLs` に追加: `https://editclone.vercel.app/ja/dashboard`

---

## 5. ローカル開発環境

```powershell
# バックエンド
cd C:\Projects\editclone
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# フロントエンド（別ターミナル）
cd frontend
copy .env.local.example .env.local
# .env.localにSupabase/Stripeのキーを入力
npm run dev
```

フロントエンド: http://localhost:3000/ja
バックエンドAPI: http://localhost:8000/docs

---

## 6. 本番公開チェックリスト

- [ ] Supabase schema.sql を実行済み
- [ ] Supabase Storage `videos` バケット作成済み
- [ ] Supabase Auth → Site URL を本番ドメインに更新
- [ ] Stripe 商品3つ作成 + Price ID を取得済み
- [ ] Stripe Webhook URL を Railway URL に設定済み
- [ ] Railway 環境変数 9つ設定済み
- [ ] Vercel Root Directory を `frontend` に設定済み
- [ ] Vercel 環境変数 4つ設定済み
- [ ] Railway デプロイ成功（`/health` が 200 を返す）
- [ ] Vercel デプロイ成功（ランディングページが表示される）
- [ ] サインアップ → ダッシュボード → アップロード → 結果ダウンロードの動作確認
