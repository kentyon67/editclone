-- EditClone Supabase Schema
-- Supabase SQL Editor で実行してください
-- 再実行しても安全（IF NOT EXISTS / OR REPLACE / IF NOT EXISTS ポリシー対応済み）

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

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'profiles' and policyname = 'Users can view own profile'
  ) then
    create policy "Users can view own profile"
      on public.profiles for select
      using (auth.uid() = id);
  end if;
end $$;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'profiles' and policyname = 'Users can update own profile'
  ) then
    create policy "Users can update own profile"
      on public.profiles for update
      using (auth.uid() = id);
  end if;
end $$;

-- 新規ユーザー登録時に自動でprofileを作成
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- =====================
-- usage_logs（月別使用量追跡）
-- =====================
create table if not exists public.usage_logs (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  year_month text not null, -- 例: '2026-06'
  video_count int not null default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(user_id, year_month)
);

alter table public.usage_logs enable row level security;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'usage_logs' and policyname = 'Users can view own usage'
  ) then
    create policy "Users can view own usage"
      on public.usage_logs for select
      using (auth.uid() = user_id);
  end if;
end $$;

-- =====================
-- jobs（処理履歴）
-- =====================
create table if not exists public.jobs (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  video_id text not null,
  video_filename text,
  status text not null default 'pending' check (status in ('pending','processing','completed','failed')),
  noise_db float default -30.0,
  min_duration float default 0.5,
  error_message text,
  created_at timestamptz default now(),
  completed_at timestamptz
);

alter table public.jobs enable row level security;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'jobs' and policyname = 'Users can view own jobs'
  ) then
    create policy "Users can view own jobs"
      on public.jobs for select
      using (auth.uid() = user_id);
  end if;
end $$;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'jobs' and policyname = 'Users can insert own jobs'
  ) then
    create policy "Users can insert own jobs"
      on public.jobs for insert
      with check (auth.uid() = user_id);
  end if;
end $$;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'jobs' and policyname = 'Users can update own jobs'
  ) then
    create policy "Users can update own jobs"
      on public.jobs for update
      using (auth.uid() = user_id);
  end if;
end $$;

-- =====================
-- Storage: videosバケット作成
-- =====================
-- Supabase Dashboard > Storage > New bucket で手動作成:
--   名前: videos
--   Public: false（非公開）
--   File size limit: 500MB

-- または SQL で:
insert into storage.buckets (id, name, public, file_size_limit)
values ('videos', 'videos', false, 524288000)
on conflict (id) do nothing;

-- =====================
-- analytics_events（行動ログ）
-- =====================
create table if not exists public.analytics_events (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete set null,
  event_type text not null,  -- upload / process_start / process_complete / process_failed / download_zip / download_mp4
  video_id text,
  job_id text,
  metadata jsonb,
  created_at timestamptz default now()
);

alter table public.analytics_events enable row level security;

-- バックエンド（service_role）のみ書き込み可能。ユーザーは読めない。
-- （読み取りは管理者用 dashboard や SQL Editor で直接行う）

-- =====================
-- increment_usage（使用本数の原子的インクリメント）
-- =====================
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

-- storageポリシー（認証済みユーザーのみ自分のファイルを操作）
do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'objects' and policyname = 'Authenticated users can upload videos'
  ) then
    create policy "Authenticated users can upload videos"
      on storage.objects for insert
      with check (auth.role() = 'authenticated' and bucket_id = 'videos');
  end if;
end $$;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'objects' and policyname = 'Users can access own videos'
  ) then
    create policy "Users can access own videos"
      on storage.objects for select
      using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'videos');
  end if;
end $$;

do $$ begin
  if not exists (
    select 1 from pg_policies where tablename = 'objects' and policyname = 'Users can delete own videos'
  ) then
    create policy "Users can delete own videos"
      on storage.objects for delete
      using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'videos');
  end if;
end $$;
