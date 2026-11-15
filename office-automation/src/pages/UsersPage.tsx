import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { getSupabase } from '../lib/supabase'
import { logActivity, formatDateTime } from '../lib/activity'
import { useProfiles } from '../lib/useProfiles'
import { RoleBadge } from '../components/RoleBadge'
import type { Profile, Role } from '../lib/types'

/** Admin-only: list all users and change their role. */
export function UsersPage() {
  const { profile: me, refreshProfile } = useAuth()
  const { profiles, error, reload } = useProfiles()
  const [query, setQuery] = useState('')
  const [savingId, setSavingId] = useState<string | null>(null)
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!profiles) return []
    if (!q) return profiles
    return profiles.filter((p) => p.email.toLowerCase().includes(q) || p.full_name.toLowerCase().includes(q))
  }, [profiles, query])

  async function changeRole(user: Profile, role: Role) {
    if (user.role === role) return
    const name = user.full_name || user.email
    const ok = window.confirm(`Change ${name} to ${role === 'admin' ? 'Administrator' : 'Staff'}?`)
    if (!ok) return
    setSavingId(user.id)
    setMessage(null)
    const { error: err } = await getSupabase().from('profiles').update({ role }).eq('id', user.id)
    setSavingId(null)
    if (err) {
      setMessage({ kind: 'error', text: err.message })
    } else {
      setMessage({ kind: 'success', text: `${name} is now ${role === 'admin' ? 'an Administrator' : 'Staff'}.` })
      await logActivity('role_change', `${user.email}: ${user.role} → ${role}`)
      if (user.id === me?.id) await refreshProfile()
    }
    await reload()
  }

  const adminCount = profiles?.filter((p) => p.role === 'admin').length ?? 0

  return (
    <div className="page">
      <section className="card">
        <div className="card-header wrap">
          <h2>All users {profiles && <span className="muted">({profiles.length})</span>}</h2>
          <label className="search">
            <Search size={18} aria-hidden />
            <input
              type="search"
              placeholder="Search by name or email"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search users"
            />
          </label>
        </div>

        <p className="muted small">
          New staff can create an account from the sign-in screen (or you can add them in the Supabase dashboard under
          Authentication → Users). Every new account starts as <strong>Staff</strong>; promote people to
          Administrator here.
        </p>

        {message && (
          <div className={`alert ${message.kind === 'error' ? 'alert-error' : 'alert-success'}`} role="status">
            {message.text}
          </div>
        )}
        {error && <div className="alert alert-error">Could not load users: {error}</div>}
        {!profiles && !error && <p className="muted">Loading users…</p>}

        {profiles && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Joined</th>
                  <th>Change role</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((u) => {
                  const lastAdmin = u.role === 'admin' && adminCount <= 1
                  return (
                    <tr key={u.id}>
                      <td data-label="Name">
                        {u.full_name || <span className="muted">—</span>}
                        {u.id === me?.id && <span className="muted small"> (you)</span>}
                      </td>
                      <td data-label="Email" className="break">
                        {u.email}
                      </td>
                      <td data-label="Role">
                        <RoleBadge role={u.role} />
                      </td>
                      <td data-label="Joined">{formatDateTime(u.created_at)}</td>
                      <td data-label="Change role">
                        <select
                          value={u.role}
                          disabled={savingId === u.id || lastAdmin}
                          title={lastAdmin ? 'There must always be at least one administrator' : undefined}
                          onChange={(e) => void changeRole(u, e.target.value as Role)}
                          aria-label={`Role for ${u.email}`}
                        >
                          <option value="staff">Staff</option>
                          <option value="admin">Administrator</option>
                        </select>
                      </td>
                    </tr>
                  )
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      No users match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
