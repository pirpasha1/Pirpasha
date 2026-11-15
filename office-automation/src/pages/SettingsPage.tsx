import { useState, type FormEvent } from 'react'
import { LogOut, Save, User } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { getSupabase } from '../lib/supabase'
import { logActivity } from '../lib/activity'
import { InstallAppCard } from '../components/InstallAppCard'
import { RoleBadge } from '../components/RoleBadge'

export function SettingsPage() {
  const { profile, refreshProfile, signOut } = useAuth()
  const [fullName, setFullName] = useState(profile?.full_name ?? '')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)

  if (!profile) return null

  async function handleSave(e: FormEvent) {
    e.preventDefault()
    if (!profile) return
    setBusy(true)
    setMessage(null)
    const { error } = await getSupabase()
      .from('profiles')
      .update({ full_name: fullName.trim() })
      .eq('id', profile.id)
    setBusy(false)
    if (error) {
      setMessage({ kind: 'error', text: error.message })
      return
    }
    await logActivity('profile_update')
    await refreshProfile()
    setMessage({ kind: 'success', text: 'Your profile has been saved.' })
  }

  const unchanged = fullName.trim() === profile.full_name

  return (
    <div className="page">
      <div className="two-col">
        <section className="card">
          <div className="card-header">
            <User size={20} aria-hidden />
            <h2>My profile</h2>
          </div>
          {message && (
            <div className={`alert ${message.kind === 'error' ? 'alert-error' : 'alert-success'}`} role="status">
              {message.text}
            </div>
          )}
          <form className="form" onSubmit={(e) => void handleSave(e)}>
            <label className="field">
              <span>Full name</span>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                maxLength={120}
                autoComplete="name"
              />
            </label>
            <div className="field">
              <span>Email</span>
              <div className="readonly">{profile.email}</div>
            </div>
            <div className="field">
              <span>Role</span>
              <div>
                <RoleBadge role={profile.role} />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={busy || unchanged}>
              <Save size={18} aria-hidden /> {busy ? 'Saving…' : 'Save changes'}
            </button>
          </form>
        </section>

        <div className="stack">
          <InstallAppCard />
          <section className="card">
            <div className="card-header">
              <LogOut size={20} aria-hidden />
              <h2>Sign out</h2>
            </div>
            <p className="muted">Sign out on shared or public devices when you are finished.</p>
            <button type="button" className="btn btn-danger" onClick={() => void signOut()}>
              <LogOut size={18} aria-hidden /> Sign out
            </button>
          </section>
        </div>
      </div>
    </div>
  )
}
