import { useAuth } from '../context/useAuth'
import { ActivityList } from '../components/ActivityList'
import { useProfiles } from '../lib/useProfiles'

export function ReportsPage() {
  const { isAdmin } = useAuth()
  const { profiles } = useProfiles()
  const nameFor = (id: string) => {
    const p = profiles?.find((x) => x.id === id)
    return p ? p.full_name || p.email : undefined
  }

  return (
    <div className="page">
      <section className="card">
        <div className="card-header">
          <h2>Activity history</h2>
        </div>
        <p className="muted small">
          {isAdmin
            ? 'As an administrator you see the activity of all users.'
            : 'You see your own activity. Administrators can see everyone’s.'}
        </p>
        <ActivityList limit={50} nameFor={isAdmin ? nameFor : undefined} />
      </section>
    </div>
  )
}
