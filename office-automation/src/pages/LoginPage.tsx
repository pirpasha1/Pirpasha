import { useState, type FormEvent } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { LogIn, Mail, UserPlus } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { allowSignUp } from '../lib/supabase'
import { LoadingScreen } from '../components/FullPageMessage'

type Mode = 'signin' | 'signup' | 'forgot'

export function LoginPage() {
  const { session, loading, signIn, signUp, sendPasswordReset } = useAuth()
  const location = useLocation()
  const [mode, setMode] = useState<Mode>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)

  if (loading) return <LoadingScreen />
  if (session) {
    const from = (location.state as { from?: string } | null)?.from ?? '/'
    return <Navigate to={from} replace />
  }

  function switchMode(next: Mode) {
    setMode(next)
    setError(null)
    setInfo(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    setBusy(true)
    try {
      if (mode === 'signin') {
        await signIn(email.trim(), password)
      } else if (mode === 'signup') {
        if (password.length < 8) throw new Error('Please use a password with at least 8 characters.')
        const { needsConfirmation } = await signUp(email.trim(), password, fullName.trim())
        if (needsConfirmation) {
          setInfo('Account created! Check your email and click the confirmation link, then sign in.')
          setMode('signin')
          setPassword('')
        }
      } else {
        await sendPasswordReset(email.trim())
        setInfo('If this email has an account, a password reset link has been sent to it.')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setBusy(false)
    }
  }

  const titles: Record<Mode, string> = {
    signin: 'Sign in',
    signup: 'Create staff account',
    forgot: 'Reset password',
  }
  const buttonLabels: Record<Mode, string> = {
    signin: 'Sign in',
    signup: 'Create account',
    forgot: 'Send reset link',
  }
  const ButtonIcon = mode === 'signin' ? LogIn : mode === 'signup' ? UserPlus : Mail

  return (
    <div className="auth-page">
      <div className="auth-card card">
        <div className="auth-brand">
          <img src="/favicon.svg" alt="" width={56} height={56} />
          <div>
            <div className="auth-app-name">Office Automation</div>
            <div className="muted small">Excel &amp; PDF tools for your office</div>
          </div>
        </div>

        <h1 className="auth-title">{titles[mode]}</h1>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}
        {info && (
          <div className="alert alert-success" role="status">
            {info}
          </div>
        )}

        <form onSubmit={(e) => void handleSubmit(e)} className="form">
          {mode === 'signup' && (
            <label className="field">
              <span>Full name</span>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                maxLength={120}
                required
              />
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              inputMode="email"
              required
            />
          </label>

          {mode !== 'forgot' && (
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                minLength={mode === 'signup' ? 8 : undefined}
                required
              />
            </label>
          )}

          <button type="submit" className="btn btn-primary btn-block btn-lg" disabled={busy}>
            <ButtonIcon size={18} aria-hidden /> {busy ? 'Please wait…' : buttonLabels[mode]}
          </button>
        </form>

        <div className="auth-links">
          {mode === 'signin' ? (
            <>
              <button type="button" className="link-btn" onClick={() => switchMode('forgot')}>
                Forgot password?
              </button>
              {allowSignUp && (
                <button type="button" className="link-btn" onClick={() => switchMode('signup')}>
                  Create an account
                </button>
              )}
            </>
          ) : (
            <button type="button" className="link-btn" onClick={() => switchMode('signin')}>
              ← Back to sign in
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
