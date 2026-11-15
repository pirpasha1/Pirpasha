import { supabase } from './supabase'
import type { ActivityEntry } from './types'

/**
 * Records an action (e.g. "login") in the activity log.
 * Logging must never break the app, so errors are only printed to the console.
 */
export async function logActivity(action: string, details = ''): Promise<void> {
  if (!supabase) return
  const { error } = await supabase.from('activity_log').insert({ action, details })
  if (error) console.warn('Could not write activity log:', error.message)
}

/**
 * Loads recent activity. Staff automatically receive only their own entries
 * (the database security rules enforce this); admins receive everyone's.
 */
export async function fetchActivity(limit = 20): Promise<ActivityEntry[]> {
  if (!supabase) return []
  const { data, error } = await supabase
    .from('activity_log')
    .select('id, user_id, action, details, created_at')
    .order('created_at', { ascending: false })
    .limit(limit)
  if (error) throw new Error(error.message)
  return data ?? []
}

const ACTION_LABELS: Record<string, string> = {
  login: 'Signed in',
  logout: 'Signed out',
  signup: 'Created account',
  profile_update: 'Updated profile',
  role_change: 'Changed a user role',
  password_reset: 'Changed password',
}

export function describeAction(action: string): string {
  return ACTION_LABELS[action] ?? action
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}
