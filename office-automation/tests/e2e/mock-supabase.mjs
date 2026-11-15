// A tiny fake Supabase server for browser tests.
// It intercepts the network requests the app makes, so the whole login /
// role / navigation flow can be tested without a real Supabase project.

export const MOCK_URL = 'https://mock-project.supabase.co'

const now = () => new Date().toISOString()

export function createMockSupabase() {
  const users = [
    { id: '11111111-1111-1111-1111-111111111111', email: 'admin@office.test', password: 'admin-pass-123', full_name: 'Alice Admin', role: 'admin' },
    { id: '22222222-2222-2222-2222-222222222222', email: 'staff@office.test', password: 'staff-pass-123', full_name: 'Sam Staff', role: 'staff' },
  ]
  const profiles = users.map((u) => ({
    id: u.id,
    email: u.email,
    full_name: u.full_name,
    role: u.role,
    created_at: '2026-01-01T09:00:00Z',
    updated_at: '2026-01-01T09:00:00Z',
  }))
  const activity = []
  const requests = []
  let nextId = 1

  function userFromToken(headers) {
    const auth = headers['authorization'] ?? ''
    const token = auth.replace(/^Bearer\s+/i, '')
    return users.find((u) => token === `token-${u.id}`) ?? null
  }

  /** Attach to a Playwright page or browser context. */
  async function install(target) {
    await target.route(`${MOCK_URL}/**`, async (route) => {
      const req = route.request()
      const url = new URL(req.url())
      const method = req.method()
      const headers = req.headers()
      requests.push({ method, path: url.pathname, search: url.search, body: req.postData() })

      const json = (status, body) =>
        route.fulfill({
          status,
          contentType: 'application/json',
          headers: { 'access-control-allow-origin': '*' },
          body: body === undefined ? '' : JSON.stringify(body),
        })

      if (method === 'OPTIONS') {
        return route.fulfill({
          status: 204,
          headers: {
            'access-control-allow-origin': '*',
            'access-control-allow-headers': '*',
            'access-control-allow-methods': '*',
          },
        })
      }

      // ---- Auth ----
      if (url.pathname === '/auth/v1/token' && url.searchParams.get('grant_type') === 'password') {
        const { email, password } = JSON.parse(req.postData() ?? '{}')
        const u = users.find((x) => x.email === email && x.password === password)
        if (!u) return json(400, { error: 'invalid_grant', error_description: 'Invalid login credentials', msg: 'Invalid login credentials', code: 'invalid_credentials' })
        const expiresAt = Math.floor(Date.now() / 1000) + 3600
        return json(200, {
          access_token: `token-${u.id}`,
          token_type: 'bearer',
          expires_in: 3600,
          expires_at: expiresAt,
          refresh_token: `refresh-${u.id}`,
          user: {
            id: u.id,
            aud: 'authenticated',
            role: 'authenticated',
            email: u.email,
            email_confirmed_at: now(),
            last_sign_in_at: now(),
            app_metadata: { provider: 'email' },
            user_metadata: { full_name: u.full_name },
            created_at: '2026-01-01T09:00:00Z',
            updated_at: now(),
          },
        })
      }
      if (url.pathname === '/auth/v1/signup') {
        // Simulates "email confirmation required": user created, no session yet.
        const { email } = JSON.parse(req.postData() ?? '{}')
        return json(200, { id: '33333333-3333-3333-3333-333333333333', email, aud: 'authenticated', role: '', app_metadata: {}, user_metadata: {}, identities: [{}], created_at: now() })
      }
      if (url.pathname === '/auth/v1/logout') return route.fulfill({ status: 204 })
      if (url.pathname === '/auth/v1/recover') return json(200, {})

      // ---- Database (PostgREST) – mimics the RLS rules ----
      const me = userFromToken(headers)
      if (url.pathname.startsWith('/rest/v1/') && !me) return json(401, { message: 'JWT required' })
      const meProfile = profiles.find((p) => p.id === me?.id)
      const isAdmin = meProfile?.role === 'admin'
      const wantsObject = (headers['accept'] ?? '').includes('vnd.pgrst.object')
      const eqId = url.searchParams.get('id')?.replace(/^eq\./, '')

      if (url.pathname === '/rest/v1/profiles') {
        if (method === 'GET') {
          let rows = profiles.filter((p) => isAdmin || p.id === me.id)
          if (eqId) rows = rows.filter((p) => p.id === eqId)
          if (wantsObject) return rows[0] ? json(200, rows[0]) : json(406, { message: 'No rows' })
          return json(200, rows)
        }
        if (method === 'PATCH') {
          const patch = JSON.parse(req.postData() ?? '{}')
          const target = profiles.find((p) => p.id === eqId)
          if (!target || (!isAdmin && target.id !== me.id)) return json(200, [])
          if ('role' in patch && patch.role !== target.role) {
            if (!isAdmin) return json(400, { message: 'Only an administrator can change roles' })
            if (target.role === 'admin' && profiles.filter((p) => p.role === 'admin').length <= 1)
              return json(400, { message: 'Cannot remove the last administrator' })
          }
          Object.assign(target, patch, { updated_at: now() })
          return route.fulfill({ status: 204 })
        }
      }

      if (url.pathname === '/rest/v1/activity_log') {
        if (method === 'POST') {
          const body = JSON.parse(req.postData() ?? '{}')
          activity.push({ id: nextId++, user_id: me.id, action: body.action, details: body.details ?? '', created_at: now() })
          return json(201)
        }
        if (method === 'GET') {
          const rows = activity
            .filter((a) => isAdmin || a.user_id === me.id)
            .sort((a, b) => b.id - a.id)
          return json(200, rows)
        }
      }

      return json(404, { message: `Mock: unhandled ${method} ${url.pathname}` })
    })
  }

  return { install, users, profiles, activity, requests }
}
