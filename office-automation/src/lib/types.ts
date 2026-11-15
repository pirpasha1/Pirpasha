export type Role = 'admin' | 'staff'

/** One row of the "profiles" table. */
export interface Profile {
  id: string
  email: string
  full_name: string
  role: Role
  created_at: string
  updated_at: string
}

/** One row of the "activity_log" table. */
export interface ActivityEntry {
  id: number
  user_id: string
  action: string
  details: string
  created_at: string
}
