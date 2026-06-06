-- EditClone Supabase Schema v5
-- Supabase SQL Editor で実行してください
-- 何度実行しても安全（IF NOT EXISTS / DO ブロック対応済み）

-- =====================
-- profiles（ユーザープロフィール）
-- =====================
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text not null,
  plan text not null default 'free' check (plan in ('free', 'pro', 'creator', 'studio')),
  stripe_customer_id text,
  stripe_subscription_id text,
  subscription_status text default 'inactive',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.profiles enable row level security;

-- =====================
-- usage_logs（月別使用量追跡）
-- =====================
create table if not exists public.usage_logs (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  year_month text not null,
  video_count int not null default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, year_month)
);

alter table public.usage_logs enable row level security;

-- =====================
-- jobs（処理履歴・永続化）
-- =====================
create table if not exists public.jobs (
  id uuid primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  video_id text not null,
  video_filename text,
  status text not null default 'pending' check (status in ('pending','processing','completed','failed')),
  noise_db float default -30.0,
  min_duration float default 0.5,
  prompt text default '',
  result_zip_path text,
  result_mp4_path text,
  result_metadata jsonb,
  error_message text,
  created_at timestamptz default now(),
  completed_at timestamptz
);

-- 既存テーブルへのカラム追加（再実行でも安全）
alter table public.jobs add column if not exists prompt text default '';
alter table public.jobs add column if not exists result_zip_path text;
alter table public.jobs add column if not exists result_mp4_path text;
alter table public.jobs add column if not exists result_metadata jsonb;

alter table public.jobs enable row level security;

-- =====================
-- style_profiles（編集スタイルプロファイル） Phase 2
-- =====================
create table if not exists public.style_profiles (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  description text default '',
  -- カット設定
  noise_db float default -30.0,
  min_silence_seconds float default 0.5,
  -- AI プロンプトテンプレート
  default_prompt text default '',
  -- メタデータ
  is_active boolean default false,
  job_count int default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- テロップスタイル設定（フォントサイズ・位置・色・太字）
alter table public.style_profiles add column if not exists caption_style jsonb default '{"font_size":28,"position":"bottom","primary_color":"#FFFFFF","outline_color":"#000000","bold":true}'::jsonb;

alter table public.style_profiles enable row level security;

-- =====================
-- reference_videos（参考動画 URL 登録 — oEmbed のみ） Phase 2
-- =====================
create table if not exists public.reference_videos (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  style_profile_id uuid references public.style_profiles(id) on delete cascade,
  url text not null,
  oembed_title text,
  oembed_thumbnail_url text,
  oembed_provider text,
  created_at timestamptz default now()
);

alter table public.reference_videos enable row level security;

-- =====================
-- feedback_logs（カット採用 / 却下ログ） Phase 2
-- =====================
create table if not exists public.feedback_logs (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  job_id text not null,
  style_profile_id uuid references public.style_profiles(id) on delete set null,
  action text not null check (action in ('accept', 'reject', 'partial')),
  notes text default '',
  created_at timestamptz default now()
);

alter table public.feedback_logs enable row level security;

-- =====================
-- projects（編集プロジェクト） Phase 3
-- =====================
create table if not exists public.projects (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  source_job_id text not null,
  style_profile_id uuid references public.style_profiles(id) on delete set null,
  sync_status text not null default 'local' check (sync_status in ('local', 'synced', 'conflict')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.projects enable row level security;

-- =====================
-- project_revisions（エクスポート履歴） Phase 3
-- =====================
create table if not exists public.project_revisions (
  id uuid default gen_random_uuid() primary key,
  project_id uuid references public.projects(id) on delete cascade not null,
  user_id uuid references public.profiles(id) on delete cascade not null,
  revision_number int not null default 1,
  source text not null default 'web' check (source in ('web', 'plugin')),
  notes text default '',
  result_path text default '',
  metadata jsonb,
  created_at timestamptz default now()
);

alter table public.project_revisions enable row level security;

-- =====================
-- analytics_events（行動ログ）
-- =====================
create table if not exists public.analytics_events (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete set null,
  event_type text not null,
  video_id text,
  job_id text,
  metadata jsonb,
  created_at timestamptz default now()
);

alter table public.analytics_events enable row level security;

-- =====================
-- 関数
-- =====================

-- 新規ユーザー登録時に自動で profile を作成
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- 使用本数の原子的インクリメント
create or replace function public.increment_usage(p_user_id uuid, p_year_month text)
returns void as $$
begin
  insert into public.usage_logs (user_id, year_month, video_count)
  values (p_user_id, p_year_month, 1)
  on conflict (user_id, year_month)
  do update set
    video_count = usage_logs.video_count + 1,
    updated_at = now();
end;
$$ language plpgsql security definer;

-- =====================
-- RLS ポリシー（DO ブロックで冪等処理）
-- =====================
do $$
begin
  -- profiles
  drop policy if exists "Users can view own profile" on public.profiles;
  drop policy if exists "Users can update own profile" on public.profiles;

  -- usage_logs
  drop policy if exists "Users can view own usage" on public.usage_logs;

  -- jobs
  drop policy if exists "Users can view own jobs" on public.jobs;
  drop policy if exists "Users can insert own jobs" on public.jobs;
  drop policy if exists "Users can update own jobs" on public.jobs;

  -- style_profiles
  drop policy if exists "Users can manage own style profiles" on public.style_profiles;

  -- reference_videos
  drop policy if exists "Users can manage own reference videos" on public.reference_videos;

  -- feedback_logs
  drop policy if exists "Users can manage own feedback" on public.feedback_logs;

  -- projects
  drop policy if exists "Users can manage own projects" on public.projects;

  -- project_revisions
  drop policy if exists "Users can manage own project revisions" on public.project_revisions;
end;
$$;

create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Users can view own usage"
  on public.usage_logs for select
  using (auth.uid() = user_id);

create policy "Users can view own jobs"
  on public.jobs for select
  using (auth.uid() = user_id);

create policy "Users can insert own jobs"
  on public.jobs for insert
  with check (auth.uid() = user_id);

create policy "Users can update own jobs"
  on public.jobs for update
  using (auth.uid() = user_id);

create policy "Users can manage own style profiles"
  on public.style_profiles for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can manage own reference videos"
  on public.reference_videos for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can manage own feedback"
  on public.feedback_logs for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can manage own projects"
  on public.projects for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Users can manage own project revisions"
  on public.project_revisions for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- =====================
-- Storage バケット
-- =====================
insert into storage.buckets (id, name, public, file_size_limit)
values ('videos', 'videos', false, 524288000)
on conflict (id) do nothing;

insert into storage.buckets (id, name, public, file_size_limit)
values ('results', 'results', false, 1073741824)
on conflict (id) do nothing;

-- =====================
-- Storage ポリシー（DO ブロックで冪等処理）
-- =====================
do $$
begin
  drop policy if exists "Authenticated users can upload videos" on storage.objects;
  drop policy if exists "Users can access own videos" on storage.objects;
  drop policy if exists "Users can delete own videos" on storage.objects;
  drop policy if exists "Users can access own results" on storage.objects;
end;
$$;

create policy "Authenticated users can upload videos"
  on storage.objects for insert
  with check (auth.role() = 'authenticated' and bucket_id = 'videos');

create policy "Users can access own videos"
  on storage.objects for select
  using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'videos');

create policy "Users can delete own videos"
  on storage.objects for delete
  using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'videos');

create policy "Users can access own results"
  on storage.objects for select
  using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'results');
