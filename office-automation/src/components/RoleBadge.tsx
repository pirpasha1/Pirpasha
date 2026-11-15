import type { Role } from '../lib/types'

export function RoleBadge({ role }: { role: Role }) {
  return (
    <span className={`badge ${role === 'admin' ? 'badge-admin' : 'badge-staff'}`}>
      {role === 'admin' ? 'Administrator' : 'Staff'}
    </span>
  )
}
