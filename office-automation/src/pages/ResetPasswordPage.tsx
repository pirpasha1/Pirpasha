import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import { getSupabase } from '../lib/supabase'
import { logActivity } from '../lib/activity'
import { FullPageMessage, LoadingScreen } from '../components/FullPageMessage'

/** Opened from the "reset password" email link. Lets the user pick a new password. */
export function ResetPasswordPage() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (loading) return <LoadingScreen />
  if (!session) {
    return (
      <FullPageMessage title="Link expired">
        <p className="muted">This password reset link is invalid or has expired. Please request a new one.</p>
        <Link to="/login" className="btn btn-primary">
          Go to sign in
        </Link>
      </FullPageMessage>
    )
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) return setError('Please use at least 8 characters.')
    if (password !== confirm) return setError('The two passwords do not match.')
    setBusy(true)
    const { error: err } = await getSupabase().auth.updateUser({ password })
    setBusy(false)
    if (err) return setError(err.message)
    await logActivity('password_reset')
    navigate('/', { replace: true })
  }

  return (
    <FullPageMessage title="Choose a new password">
      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={(e) => void handleSubmit(e)} className="form">
        <label className="field">
          <span>New password</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" required />
        </label>
        <label className="field">
          <span>Repeat new password</span>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={busy}>
          {busy ? 'Saving…' : 'Save new password'}
        </button>
      </form>
    </FullPageMessage>
  )
}
