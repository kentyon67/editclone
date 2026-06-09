-- EditClone Schema v8 Migration
-- api_keys + webhooks テーブル追加
-- 何度実行しても安全（IF NOT EXISTS / DO ブロック対応済み）

-- api_keys（外部APIキー管理）
create table if not exists public.api_keys (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  name text not null,
  key_hash text not null unique,
  key_prefix text not null,
  revoked boolean default false,
  last_used_at timestamptz,
  created_at timestamptz default now()
);

alter table public.api_keys enable row level security;

do $$
begin
  drop policy if exists "Users can manage own api keys" on public.api_keys;
end;
$$;

create policy "Users can manage own api keys"
  on public.api_keys for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- webhooks（Webhook登録）
create table if not exists public.webhooks (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references public.profiles(id) on delete cascade not null,
  url text not null,
  events text[] not null default '{}',
  secret text not null,
  active boolean default true,
  created_at timestamptz default now()
);

alter table public.webhooks enable row level security;

do $$
begin
  drop policy if exists "Users can manage own webhooks" on public.webhooks;
end;
$$;

create policy "Users can manage own webhooks"
  on public.webhooks for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
