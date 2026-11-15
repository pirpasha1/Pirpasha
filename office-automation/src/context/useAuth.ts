import { useContext } from 'react'
import { AuthContext, type AuthState } from './auth-context'

/** Gives any screen access to the logged-in user, their role and login actions. */
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
