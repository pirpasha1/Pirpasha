import { useCallback, useEffect, useState } from 'react'
import { getSupabase } from './supabase'
import type { Profile } from './types'

async function loadProfiles(): Promise<Profile[]> {
  const { data, error } = await getSupabase()
    .from('profiles')
    .select('id, email, full_name, role, created_at, updated_at')
    .order('created_at', { ascending: true })
  if (error) throw new Error(error.message)
  return (data ?? []) as Profile[]
}

/**
 * Loads user profiles. Admins get everyone; staff only get themselves
 * (the database security rules decide this, not this code).
 */
export function useProfiles() {
  const [profiles, setProfiles] = useState<Profile[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const apply = useCallback((p: Promise<Profile[]>) => {
    return p.then(
      (rows) => {
        setProfiles(rows)
        setError(null)
      },
      (e: Error) => setError(e.message),
    )
  }, [])

  useEffect(() => {
    void apply(loadProfiles())
  }, [apply])

  const reload = useCallback(() => apply(loadProfiles()), [apply])

  return { profiles, error, reload }
}
