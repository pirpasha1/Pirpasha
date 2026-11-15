import { createContext } from 'react'
import type { Session } from '@supabase/supabase-js'
import type { Profile } from '../lib/types'

export interface AuthState {
  /** The logged-in session, or null when logged out. */
  session: Session | null
  /** The user's profile row (name + role). */
  profile: Profile | null
  /** True while we are still checking whether someone is logged in. */
  loading: boolean
  /** Set when the profile could not be loaded (e.g. database not set up). */
  profileError: string | null
  isAdmin: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, fullName: string) => Promise<{ needsConfirmation: boolean }>
  signOut: () => Promise<void>
  sendPasswordReset: (email: string) => Promise<void>
  refreshProfile: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)
