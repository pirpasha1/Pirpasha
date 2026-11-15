import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { getSupabase } from '../lib/supabase'
import { logActivity } from '../lib/activity'
import type { Profile } from '../lib/types'
import { AuthContext, type AuthState } from './auth-context'

interface LoadedProfile {
  userId: string
  profile: Profile | null
  error: string | null
}

/**
 * Keeps track of who is logged in and exposes login / logout functions.
 * Wrap the whole app in <AuthProvider> so every screen can use `useAuth()`.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const supabase = getSupabase()
  const [session, setSession] = useState<Session | null>(null)
  const [sessionLoading, setSessionLoading] = useState(true)
  // The profile is stored together with the user id it belongs to, so a
  // profile from a previous login is never shown to a different user.
  const [loaded, setLoaded] = useState<LoadedProfile | null>(null)

  // 1. Find out whether someone is already logged in, and listen for changes.
  useEffect(() => {
    let active = true
    supabase.auth.getSession().then(({ data }) => {
      if (!active) return
      setSession(data.session)
      setSessionLoading(false)
    })
    const { data: sub } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession)
      setSessionLoading(false)
    })
    return () => {
      active = false
      sub.subscription.unsubscribe()
    }
  }, [supabase])

  const userId = session?.user.id ?? null

  // 2. Whenever the logged-in user changes, load their profile (name + role).
  const fetchProfile = useCallback(
    async (id: string): Promise<LoadedProfile> => {
      const { data, error } = await supabase
        .from('profiles')
        .select('id, email, full_name, role, created_at, updated_at')
        .eq('id', id)
        .maybeSingle()
      if (error) return { userId: id, profile: null, error: error.message }
      if (!data)
        return {
          userId: id,
          profile: null,
          error: 'Your account has no profile yet. An administrator must run the database setup script (see README).',
        }
      return { userId: id, profile: data as Profile, error: null }
    },
    [supabase],
  )

  useEffect(() => {
    if (!userId) return
    let active = true
    fetchProfile(userId).then((result) => {
      if (active) setLoaded(result)
    })
    return () => {
      active = false
    }
  }, [userId, fetchProfile])

  const current = loaded && loaded.userId === userId ? loaded : null
  const profile = current?.profile ?? null
  const profileError = current?.error ?? null

  const signIn = useCallback(
    async (email: string, password: string) => {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw new Error(friendlyAuthError(error.message))
      await logActivity('login')
    },
    [supabase],
  )

  const signUp = useCallback(
    async (email: string, password: string, fullName: string) => {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: fullName },
          emailRedirectTo: window.location.origin,
        },
      })
      if (error) throw new Error(friendlyAuthError(error.message))
      // If email confirmation is ON in Supabase, there is no session yet.
      const needsConfirmation = !data.session
      if (!needsConfirmation) await logActivity('signup')
      return { needsConfirmation }
    },
    [supabase],
  )

  const signOut = useCallback(async () => {
    await logActivity('logout')
    const { error } = await supabase.auth.signOut()
    if (error) throw new Error(error.message)
  }, [supabase])

  const sendPasswordReset = useCallback(
    async (email: string) => {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      })
      if (error) throw new Error(friendlyAuthError(error.message))
    },
    [supabase],
  )

  const refreshProfile = useCallback(async () => {
    if (userId) setLoaded(await fetchProfile(userId))
  }, [userId, fetchProfile])

  const value = useMemo<AuthState>(
    () => ({
      session,
      profile,
      // Still loading while we check the session, or while a logged-in
      // user's profile has not arrived yet.
      loading: sessionLoading || (!!userId && current === null),
      profileError,
      isAdmin: profile?.role === 'admin',
      signIn,
      signUp,
      signOut,
      sendPasswordReset,
      refreshProfile,
    }),
    [session, profile, sessionLoading, userId, current, profileError, signIn, signUp, signOut, sendPasswordReset, refreshProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Turns technical Supabase error messages into plain language. */
function friendlyAuthError(message: string): string {
  const m = message.toLowerCase()
  if (m.includes('invalid login credentials')) return 'Wrong email or password. Please try again.'
  if (m.includes('email not confirmed'))
    return 'Please confirm your email address first. Check your inbox for the confirmation link.'
  if (m.includes('user already registered')) return 'An account with this email already exists. Please sign in.'
  if (m.includes('password should be at least'))
    return 'The password is too short. Use at least 8 characters.'
  if (m.includes('rate limit')) return 'Too many attempts. Please wait a minute and try again.'
  if (m.includes('failed to fetch'))
    return 'Cannot reach the server. Check your internet connection.'
  return message
}
