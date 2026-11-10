-- Run in Supabase SQL Editor. Supabase Auth manages user identities.
-- All student progress is scoped to auth.uid() and protected by RLS.
create table if not exists public.user_progress (
    user_id uuid primary key references auth.users(id) on delete cascade,
    payload jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

alter table public.user_progress enable row level security;

-- Explicitly revoke anonymous access. Only logged-in users may use this table.
revoke all on public.user_progress from anon;
grant select, insert, update, delete on public.user_progress to authenticated;

drop policy if exists "Read own progress" on public.user_progress;
create policy "Read own progress" on public.user_progress
for select to authenticated using ((select auth.uid()) = user_id);

drop policy if exists "Insert own progress" on public.user_progress;
create policy "Insert own progress" on public.user_progress
for insert to authenticated with check ((select auth.uid()) = user_id);

drop policy if exists "Update own progress" on public.user_progress;
create policy "Update own progress" on public.user_progress
for update to authenticated using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists "Delete own progress" on public.user_progress;
create policy "Delete own progress" on public.user_progress
for delete to authenticated using ((select auth.uid()) = user_id);

create or replace function public.set_progress_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists user_progress_updated_at on public.user_progress;
create trigger user_progress_updated_at before update on public.user_progress
for each row execute function public.set_progress_updated_at();
