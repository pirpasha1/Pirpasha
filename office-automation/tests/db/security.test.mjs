// Database security tests.
// Runs the real migration SQL in an in-memory PostgreSQL (PGlite), with a
// small imitation of Supabase's "auth" schema, then checks that the
// Row Level Security rules behave as intended.
//
// Run with:  npm run test:db
import { test, before } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { PGlite } from '@electric-sql/pglite'

const db = new PGlite()

// Minimal stand-in for what Supabase provides out of the box.
const SUPABASE_STUB = `
  create role anon nologin;
  create role authenticated nologin;
  create schema auth;
  grant usage on schema auth to anon, authenticated;
  grant usage on schema public to anon, authenticated;
  create table auth.users (
    id uuid primary key,
    email text,
    raw_user_meta_data jsonb default '{}'::jsonb,
    created_at timestamptz default now()
  );
  create function auth.uid() returns uuid language sql stable as $$
    select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
  $$;
  grant execute on function auth.uid() to anon, authenticated;
  alter default privileges in schema public grant all on tables to anon, authenticated;
  alter default privileges in schema public grant all on sequences to anon, authenticated;
`

const ADMIN = '00000000-0000-0000-0000-00000000000a'
const STAFF = '00000000-0000-0000-0000-00000000000b'
const STAFF2 = '00000000-0000-0000-0000-00000000000c'

/** Run SQL as a logged-in user (or as an anonymous visitor when id is null). */
async function as(id, sql, params = []) {
  await db.exec('reset role')
  await db.query(`select set_config('request.jwt.claim.sub', $1, false)`, [id ?? ''])
  await db.exec(`set role ${id ? 'authenticated' : 'anon'}`)
  try {
    return await db.query(sql, params)
  } finally {
    await db.exec('reset role')
    await db.query(`select set_config('request.jwt.claim.sub', '', false)`)
  }
}

async function signUp(id, email, name) {
  await db.query(
    `insert into auth.users (id, email, raw_user_meta_data) values ($1, $2, $3)`,
    [id, email, JSON.stringify({ full_name: name })],
  )
}

before(async () => {
  await db.exec(SUPABASE_STUB)
  const sql = await readFile(new URL('../../supabase/migrations/0001_foundation.sql', import.meta.url), 'utf8')
  await db.exec(sql)
  // Running it a second time must also work ("safe to run again").
  await db.exec(sql)
  await signUp(ADMIN, 'boss@office.test', 'Boss')
  await signUp(STAFF, 'sam@office.test', 'Sam')
  await signUp(STAFF2, 'kim@office.test', 'Kim')
})

test('first user becomes admin, later users become staff', async () => {
  const { rows } = await db.query(`select email, role, full_name from public.profiles order by email`)
  assert.deepEqual(rows, [
    { email: 'boss@office.test', role: 'admin', full_name: 'Boss' },
    { email: 'kim@office.test', role: 'staff', full_name: 'Kim' },
    { email: 'sam@office.test', role: 'staff', full_name: 'Sam' },
  ])
})

test('logged-out visitors cannot read anything', async () => {
  await assert.rejects(as(null, `select * from public.profiles`), /permission denied/)
  await assert.rejects(as(null, `select * from public.activity_log`), /permission denied/)
})

test('staff can only see their own profile', async () => {
  const { rows } = await as(STAFF, `select email from public.profiles`)
  assert.deepEqual(rows, [{ email: 'sam@office.test' }])
})

test('admin can see all profiles', async () => {
  const { rows } = await as(ADMIN, `select email from public.profiles`)
  assert.equal(rows.length, 3)
})

test('staff can change their own name', async () => {
  await as(STAFF, `update public.profiles set full_name = 'Samuel' where id = $1`, [STAFF])
  const { rows } = await db.query(`select full_name from public.profiles where id = $1`, [STAFF])
  assert.equal(rows[0].full_name, 'Samuel')
})

test('staff cannot change someone else’s profile', async () => {
  const res = await as(STAFF, `update public.profiles set full_name = 'Hacked' where id = $1`, [STAFF2])
  assert.equal(res.affectedRows, 0)
  const { rows } = await db.query(`select full_name from public.profiles where id = $1`, [STAFF2])
  assert.equal(rows[0].full_name, 'Kim')
})

test('staff cannot make themselves admin', async () => {
  await assert.rejects(
    as(STAFF, `update public.profiles set role = 'admin' where id = $1`, [STAFF]),
    /Only an administrator can change roles/,
  )
})

test('staff cannot change their email through the profile', async () => {
  await assert.rejects(
    as(STAFF, `update public.profiles set email = 'x@evil.test' where id = $1`, [STAFF]),
    /not allowed/,
  )
})

test('users cannot insert or delete profiles directly', async () => {
  await assert.rejects(
    as(STAFF, `insert into public.profiles (id, email, role) values (gen_random_uuid(), 'a@b.c', 'admin')`),
    /permission denied/,
  )
  await assert.rejects(as(ADMIN, `delete from public.profiles where id = $1`, [STAFF2]), /permission denied/)
})

test('admin can promote and demote, but not remove the last admin', async () => {
  await assert.rejects(
    as(ADMIN, `update public.profiles set role = 'staff' where id = $1`, [ADMIN]),
    /last administrator/,
  )
  await as(ADMIN, `update public.profiles set role = 'admin' where id = $1`, [STAFF2])
  // Now there are two admins, so demoting one is allowed.
  await as(ADMIN, `update public.profiles set role = 'staff' where id = $1`, [STAFF2])
  const { rows } = await db.query(`select role from public.profiles where id = $1`, [STAFF2])
  assert.equal(rows[0].role, 'staff')
})

test('activity log: users write only their own entries', async () => {
  await as(STAFF, `insert into public.activity_log (action) values ('login')`)
  await as(ADMIN, `insert into public.activity_log (action) values ('login')`)
  await assert.rejects(
    as(STAFF, `insert into public.activity_log (user_id, action) values ($1, 'fake')`, [ADMIN]),
    /row-level security/,
  )
})

test('activity log: staff see own entries, admin sees all', async () => {
  const staffRows = await as(STAFF, `select user_id from public.activity_log`)
  assert.ok(staffRows.rows.length >= 1)
  assert.ok(staffRows.rows.every((r) => r.user_id === STAFF))
  const adminRows = await as(ADMIN, `select distinct user_id from public.activity_log`)
  assert.equal(adminRows.rows.length, 2)
})

test('activity log cannot be edited or deleted from the app', async () => {
  await assert.rejects(as(ADMIN, `update public.activity_log set action = 'x'`), /permission denied/)
  await assert.rejects(as(ADMIN, `delete from public.activity_log`), /permission denied/)
})

test('deleting a user in Supabase Auth removes their profile', async () => {
  await db.query(`delete from auth.users where id = $1`, [STAFF2])
  const { rows } = await db.query(`select count(*)::int as n from public.profiles where id = $1`, [STAFF2])
  assert.equal(rows[0].n, 0)
})
