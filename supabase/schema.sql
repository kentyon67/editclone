-- EditClone Supabase Schema
-- Supabase SQL Editor で実行してください

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

create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

-- 新規ユーザー登録時に自動でprofileを作成
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

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

create policy "Users can view own usage"
  on public.usage_logs for select
  using (auth.uid() = user_id);

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

create policy "Users can view own jobs"
  on public.jobs for select
  using (auth.uid() = user_id);

create policy "Users can insert own jobs"
  on public.jobs for insert
  with check (auth.uid() = user_id);

create policy "Users can update own jobs"
  on public.jobs for update
  using (auth.uid() = user_id);

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

-- storageポリシー（認証済みユーザーのみ自分のファイルを操作）
create policy "Authenticated users can upload videos"
  on storage.objects for insert
  with check (auth.role() = 'authenticated' and bucket_id = 'videos');

create policy "Users can access own videos"
  on storage.objects for select
  using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'videos');

create policy "Users can delete own videos"
  on storage.objects for delete
  using (auth.uid()::text = (storage.foldername(name))[1] and bucket_id = 'videos');
