// Browser tests: build the app, start it, and click through it in Chromium.
// Run with:  npm run test:e2e
import { test, before, after } from 'node:test'
import assert from 'node:assert/strict'
import { spawn, execSync } from 'node:child_process'
import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'
import { createMockSupabase, MOCK_URL } from './mock-supabase.mjs'

const ROOT = new URL('../..', import.meta.url).pathname
const PORT = 4321
const BASE = `http://localhost:${PORT}`
const SHOTS = process.env.SCREENSHOT_DIR // optional: save screenshots here

let server
let browser

async function waitForServer(url, ms = 20000) {
  const start = Date.now()
  while (Date.now() - start < ms) {
    try {
      const r = await fetch(url)
      if (r.ok) return
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 200))
  }
  throw new Error('preview server did not start')
}

before(async () => {
  // Build with fake Supabase settings that point at our mock.
  execSync('npx vite build --outDir dist-test --emptyOutDir', {
    cwd: ROOT,
    stdio: 'ignore',
    env: { ...process.env, VITE_SUPABASE_URL: MOCK_URL, VITE_SUPABASE_ANON_KEY: 'mock-anon-key-for-tests-only-0123456789' },
  })
  server = spawn('npx', ['vite', 'preview', '--outDir', 'dist-test', '--port', String(PORT), '--strictPort'], {
    cwd: ROOT,
    stdio: 'ignore',
  })
  await waitForServer(BASE)
  browser = await chromium.launch()
  if (SHOTS) await mkdir(SHOTS, { recursive: true })
})

after(async () => {
  await browser?.close()
  server?.kill()
})

async function newPage(viewport = { width: 1280, height: 800 }) {
  const context = await browser.newContext({ viewport, serviceWorkers: 'block' })
  const mock = createMockSupabase()
  await mock.install(context)
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  return { page, mock, context, errors }
}

async function login(page, email, password) {
  await page.goto(BASE + '/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true })
}

test('logged-out visitors are sent to the sign-in screen', async () => {
  const { page, context } = await newPage()
  await page.goto(BASE + '/reports')
  await page.waitForURL('**/login')
  await page.getByRole('heading', { name: 'Sign in' }).waitFor()
  await shot(page, 'login-desktop')
  await context.close()
})

test('wrong password shows a friendly error', async () => {
  const { page, context } = await newPage()
  await login(page, 'staff@office.test', 'wrong-password')
  await page.getByRole('alert').getByText('Wrong email or password').waitFor()
  await context.close()
})

test('forgot password sends a reset email', async () => {
  const { page, mock, context } = await newPage()
  await page.goto(BASE + '/login')
  await page.getByRole('button', { name: 'Forgot password?' }).click()
  await page.getByLabel('Email').fill('staff@office.test')
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await page.getByText('password reset link has been sent').waitFor()
  assert.ok(mock.requests.some((r) => r.path === '/auth/v1/recover'))
  await context.close()
})

test('create account asks the user to confirm their email', async () => {
  const { page, mock, context } = await newPage()
  await page.goto(BASE + '/login')
  await page.getByRole('button', { name: 'Create an account' }).click()
  await page.getByLabel('Full name').fill('New Person')
  await page.getByLabel('Email').fill('new@office.test')
  await page.getByLabel('Password').fill('short')
  await page.getByRole('button', { name: 'Create account' }).click()
  // Browser validation blocks passwords under 8 characters.
  assert.equal(mock.requests.some((r) => r.path === '/auth/v1/signup'), false)
  await page.getByLabel('Password').fill('long-enough-pass')
  await page.getByRole('button', { name: 'Create account' }).click()
  await page.getByText('Check your email').waitFor()
  const body = JSON.parse(mock.requests.find((r) => r.path === '/auth/v1/signup').body)
  assert.equal(body.data.full_name, 'New Person')
  await context.close()
})

test('staff: sees dashboard, every menu link works, no admin pages', async () => {
  const { page, mock, context, errors } = await newPage()
  await login(page, 'staff@office.test', 'staff-pass-123')
  await page.getByRole('heading', { name: /Welcome, Sam/ }).waitFor()
  await shot(page, 'dashboard-staff-desktop')

  const nav = page.getByRole('navigation')
  assert.equal(await nav.getByRole('link', { name: 'User Management' }).count(), 0)

  const pages = [
    ['Excel Tools', '/excel'],
    ['PDF Tools', '/pdf'],
    ['Activity & Reports', '/reports'],
    ['Settings', '/settings'],
    ['Dashboard', '/'],
  ]
  for (const [label, path] of pages) {
    await nav.getByRole('link', { name: label }).click()
    await page.waitForURL(BASE + path)
    await page.locator('.topbar-title', { hasText: label }).waitFor()
    assert.equal(await page.getByText('Page not found').count(), 0, `${label} should not be 404`)
  }

  // Typing the admin address directly must not open it.
  await page.goto(BASE + '/users')
  await page.waitForURL(BASE + '/')
  assert.ok(mock.activity.some((a) => a.action === 'login'), 'login is recorded')
  assert.deepEqual(errors, [])
  await context.close()
})

test('staff: can update their name in Settings', async () => {
  const { page, mock, context } = await newPage()
  await login(page, 'staff@office.test', 'staff-pass-123')
  await page.getByRole('heading', { name: /Welcome/ }).waitFor()
  await page.getByRole('navigation').getByRole('link', { name: 'Settings' }).click()
  const name = page.getByLabel('Full name')
  await name.fill('Samantha Staff')
  await page.getByRole('button', { name: 'Save changes' }).click()
  await page.getByText('Your profile has been saved.').waitFor()
  assert.equal(mock.profiles.find((p) => p.email === 'staff@office.test').full_name, 'Samantha Staff')
  await page.locator('.user-name', { hasText: 'Samantha Staff' }).waitFor()
  await shot(page, 'settings-desktop')
  await context.close()
})

test('admin: manages user roles; last admin is protected', async () => {
  const { page, mock, context, errors } = await newPage()
  await login(page, 'admin@office.test', 'admin-pass-123')
  await page.getByRole('heading', { name: /Welcome, Alice/ }).waitFor()
  await page.getByText('Total users').waitFor()
  await shot(page, 'dashboard-admin-desktop')

  await page.getByRole('navigation').getByRole('link', { name: 'User Management' }).click()
  await page.getByRole('cell', { name: 'staff@office.test' }).waitFor()

  // The only admin's role selector is locked.
  assert.equal(await page.getByLabel('Role for admin@office.test').isDisabled(), true)

  page.once('dialog', (d) => d.accept())
  await page.getByLabel('Role for staff@office.test').selectOption('admin')
  await page.getByText('Sam Staff is now an Administrator.').waitFor()
  assert.equal(mock.profiles.find((p) => p.email === 'staff@office.test').role, 'admin')
  assert.ok(mock.activity.some((a) => a.action === 'role_change'))
  await shot(page, 'users-desktop')

  // Search filter
  await page.getByLabel('Search users').fill('alice')
  assert.equal(await page.getByRole('cell', { name: 'staff@office.test' }).count(), 0)
  assert.deepEqual(errors, [])
  await context.close()
})

test('sign out returns to the sign-in screen and is logged', async () => {
  const { page, mock, context } = await newPage()
  await login(page, 'staff@office.test', 'staff-pass-123')
  await page.getByRole('heading', { name: /Welcome/ }).waitFor()
  await page.locator('.sidebar').getByRole('button', { name: 'Sign out' }).click()
  await page.waitForURL('**/login')
  assert.ok(mock.activity.some((a) => a.action === 'logout'))
  // Protected pages are no longer reachable.
  await page.goto(BASE + '/settings')
  await page.waitForURL('**/login')
  await context.close()
})

test('phone layout: menu opens, navigates and closes', async () => {
  const { page, context } = await newPage({ width: 390, height: 844 })
  await login(page, 'admin@office.test', 'admin-pass-123')
  await page.getByRole('heading', { name: /Welcome/ }).waitFor()
  await shot(page, 'dashboard-mobile')

  const sidebar = page.locator('.sidebar')
  const isOnScreen = async () => (await sidebar.boundingBox()).x >= 0
  assert.equal(await isOnScreen(), false, 'menu hidden at start')
  await page.getByRole('button', { name: 'Open menu' }).click()
  await page.waitForTimeout(300)
  assert.equal(await isOnScreen(), true, 'menu visible after tapping')
  await shot(page, 'menu-mobile')
  await sidebar.getByRole('link', { name: 'User Management' }).click()
  await page.waitForURL(BASE + '/users')
  await page.waitForTimeout(300)
  assert.equal(await isOnScreen(), false, 'menu closes after choosing a page')
  await shot(page, 'users-mobile')

  // No sideways scrolling on a phone.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  assert.equal(overflow, false)
  await context.close()
})

test('without Supabase settings, a setup guide is shown instead of crashing', async () => {
  execSync('npx vite build --outDir dist-test-nosetup --emptyOutDir', {
    cwd: ROOT,
    stdio: 'ignore',
    env: { ...process.env, VITE_SUPABASE_URL: '', VITE_SUPABASE_ANON_KEY: '' },
  })
  const port = PORT + 1
  const s2 = spawn('npx', ['vite', 'preview', '--outDir', 'dist-test-nosetup', '--port', String(port), '--strictPort'], {
    cwd: ROOT,
    stdio: 'ignore',
  })
  try {
    await waitForServer(`http://localhost:${port}`)
    const page = await browser.newPage()
    await page.goto(`http://localhost:${port}/`)
    await page.getByRole('heading', { name: 'Setup required' }).waitFor()
    await shot(page, 'setup-required')
    await page.close()
  } finally {
    s2.kill()
  }
})

test('PWA: manifest, icons and service worker are served', async () => {
  const manifest = await (await fetch(BASE + '/manifest.webmanifest')).json()
  assert.equal(manifest.name, 'Office Automation')
  assert.equal(manifest.display, 'standalone')
  for (const icon of manifest.icons) {
    const r = await fetch(`${BASE}/${icon.src}`)
    assert.equal(r.status, 200, icon.src)
    assert.equal(r.headers.get('content-type'), 'image/png')
  }
  const sw = await fetch(BASE + '/sw.js')
  assert.equal(sw.status, 200)

  // The page links the manifest and registers the service worker.
  const page = await browser.newPage()
  await page.goto(BASE + '/login')
  assert.ok(await page.locator('link[rel="manifest"]').count())
  const registered = await page.evaluate(async () => {
    const reg = await navigator.serviceWorker.ready
    return !!reg.active
  })
  assert.equal(registered, true)
  await page.close()
})
