import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// These values come from the ".env" file (see ".env.example").
// Vite only exposes variables that start with "VITE_" to the browser.
const url = (import.meta.env.VITE_SUPABASE_URL ?? '').trim()
const anonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY ?? '').trim()

/** True when both Supabase settings are filled in. */
export const isSupabaseConfigured = url.startsWith('http') && anonKey.length > 20

/**
 * The single Supabase client used by the whole app.
 * It is `null` when the app has not been configured yet; the app then shows
 * a friendly "Setup required" screen instead of crashing.
 */
export const supabase: SupabaseClient | null = isSupabaseConfigured
  ? createClient(url, anonKey, {
      auth: {
        persistSession: true, // stay logged in after closing the app
        autoRefreshToken: true,
        detectSessionInUrl: true, // needed for password-reset links
      },
    })
  : null

/** Use inside screens that are only shown when Supabase is configured. */
export function getSupabase(): SupabaseClient {
  if (!supabase) throw new Error('Supabase is not configured')
  return supabase
}

/** Whether visitors may create their own (staff) account from the login screen. */
export const allowSignUp = (import.meta.env.VITE_ALLOW_SIGNUP ?? 'true').trim() !== 'false'
