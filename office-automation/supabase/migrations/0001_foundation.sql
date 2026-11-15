-- =====================================================================
-- Office Automation – Foundation database setup
-- ---------------------------------------------------------------------
-- What this file does (in simple words):
--   1. Creates two roles: "admin" and "staff".
--   2. Creates a "profiles" table: one row per user, holding their role.
--   3. Automatically creates a profile when someone signs up.
--      The VERY FIRST user becomes "admin"; everyone after is "staff".
--   4. Creates an "activity_log" table (who did what, and when).
--   5. Turns on Row Level Security (RLS) so that:
--        - staff can only see/edit their OWN profile and activity;
--        - admins can see everyone and change roles;
--        - nobody can make themselves admin;
--        - the last remaining admin cannot be demoted.
--
-- How to run: Supabase Dashboard -> SQL Editor -> New query ->
--             paste this whole file -> Run.  It is safe to run again.
-- =====================================================================

-- ---------- 1. Role type --------------------------------------------
do $$
begin
  if not exists (select 1 from pg_type where typname = 'app_role') then
    create type public.app_role as enum ('admin', 'staff');
  end if;
end$$;

-- ---------- 2. Profiles table ---------------------------------------
create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null,
  full_name   text not null default '',
  role        public.app_role not null default 'staff',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint full_name_length check (char_length(full_name) <= 120)
);

-- ---------- 3. Activity log table -----------------------------------
create table if not exists public.activity_log (
  id          bigint generated always as identity primary key,
  user_id     uuid not null references auth.users (id) on delete cascade
              default auth.uid(),
  action      text not null,
  details     text not null default '',
  created_at  timestamptz not null default now(),
  constraint action_length  check (char_length(action)  between 1 and 60),
  constraint details_length check (char_length(details) <= 500)
);
create index if not exists activity_log_user_created_idx
  on public.activity_log (user_id, created_at desc);

-- ---------- 4. Helper: is the current user an admin? ----------------
-- "security definer" lets this function read profiles without being
-- blocked by RLS (otherwise the policies below would loop forever).
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

revoke all on function public.is_admin() from public, anon;
grant execute on function public.is_admin() to authenticated;

-- ---------- 5. Auto-create a profile for every new user -------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  first_user boolean;
begin
  -- Lock so two simultaneous sign-ups cannot both become the first admin.
  lock table public.profiles in share row exclusive mode;
  select not exists (select 1 from public.profiles) into first_user;

  insert into public.profiles (id, email, full_name, role)
  values (
    new.id,
    coalesce(new.email, ''),
    left(coalesce(new.raw_user_meta_data ->> 'full_name', ''), 120),
    case when first_user then 'admin'::public.app_role
         else 'staff'::public.app_role end
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- 6. Protect sensitive profile columns --------------------
-- Users may edit their own name, but:
--   * id, email and created_at can never be changed from the app;
--   * only admins may change a role;
--   * the last admin cannot be demoted (so you never lock yourself out).
create or replace function public.protect_profile_columns()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  -- Requests made with the service key / SQL editor (no logged-in user)
  -- are trusted maintenance operations and skip these checks.
  if auth.uid() is null then
    new.updated_at := now();
    return new;
  end if;

  if new.id <> old.id or new.email <> old.email
     or new.created_at <> old.created_at then
    raise exception 'You are not allowed to change id, email or created_at';
  end if;

  if new.role <> old.role then
    if not public.is_admin() then
      raise exception 'Only an administrator can change roles';
    end if;
    if old.role = 'admin' and new.role <> 'admin' and
       (select count(*) from public.profiles where role = 'admin') <= 1 then
      raise exception 'Cannot remove the last administrator';
    end if;
  end if;

  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists protect_profile_columns on public.profiles;
create trigger protect_profile_columns
  before update on public.profiles
  for each row execute function public.protect_profile_columns();

-- ---------- 7. Row Level Security -----------------------------------
alter table public.profiles     enable row level security;
alter table public.activity_log enable row level security;

-- Anonymous (logged-out) visitors get no access at all.
revoke all on public.profiles     from anon;
revoke all on public.activity_log from anon;

-- Logged-in users: only the operations we allow below.
revoke all on public.profiles from authenticated;
grant select, update on public.profiles to authenticated;

revoke all on public.activity_log from authenticated;
grant select, insert on public.activity_log to authenticated;

-- profiles: read own row, or every row if admin.
drop policy if exists "profiles_select_own_or_admin" on public.profiles;
create policy "profiles_select_own_or_admin" on public.profiles
  for select to authenticated
  using (id = (select auth.uid()) or (select public.is_admin()));

-- profiles: update own row, or any row if admin.
-- (The trigger above stops staff from changing their role.)
drop policy if exists "profiles_update_own_or_admin" on public.profiles;
create policy "profiles_update_own_or_admin" on public.profiles
  for update to authenticated
  using (id = (select auth.uid()) or (select public.is_admin()))
  with check (id = (select auth.uid()) or (select public.is_admin()));

-- No insert/delete policies on profiles: rows are created by the trigger
-- and removed automatically when the user is deleted in Supabase Auth.

-- activity_log: read own entries, or every entry if admin.
drop policy if exists "activity_select_own_or_admin" on public.activity_log;
create policy "activity_select_own_or_admin" on public.activity_log
  for select to authenticated
  using (user_id = (select auth.uid()) or (select public.is_admin()));

-- activity_log: users can only add entries for themselves.
-- No update/delete policies: the log cannot be edited or erased from the app.
drop policy if exists "activity_insert_own" on public.activity_log;
create policy "activity_insert_own" on public.activity_log
  for insert to authenticated
  with check (user_id = (select auth.uid()));

-- ---------- 8. Backfill: users who signed up before this script -----
insert into public.profiles (id, email, role)
select u.id, coalesce(u.email, ''),
       case when row_number() over (order by u.created_at) = 1
                 and not exists (select 1 from public.profiles where role = 'admin')
            then 'admin'::public.app_role else 'staff'::public.app_role end
from auth.users u
where not exists (select 1 from public.profiles p where p.id = u.id);
