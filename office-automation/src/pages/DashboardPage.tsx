import { Link } from 'react-router-dom'
import { ChevronRight, Clock, ShieldCheck, Users } from 'lucide-react'
import { useAuth } from '../context/useAuth'
import { modulesForRole } from '../config/modules'
import { ActivityList } from '../components/ActivityList'
import { InstallAppCard } from '../components/InstallAppCard'
import { RoleBadge } from '../components/RoleBadge'
import { useProfiles } from '../lib/useProfiles'
import { formatDateTime } from '../lib/activity'

export function DashboardPage() {
  const { profile, session, isAdmin } = useAuth()
  const { profiles } = useProfiles()
  if (!profile) return null

  const firstName = (profile.full_name || profile.email).split(/[\s@]/)[0]
  const cards = modulesForRole(profile.role).filter((m) => m.onDashboard)
  const lastSignIn = session?.user.last_sign_in_at
  const nameFor = (id: string) => {
    const p = profiles?.find((x) => x.id === id)
    return p ? p.full_name || p.email : undefined
  }

  return (
    <div className="page">
      <section className="welcome">
        <div>
          <h2>Welcome, {firstName} 👋</h2>
          <p className="muted">Choose a module below to get started.</p>
        </div>
        <RoleBadge role={profile.role} />
      </section>

      <section className="stats" aria-label="Summary">
        <div className="stat card">
          <ShieldCheck aria-hidden />
          <div>
            <div className="stat-label">Your role</div>
            <div className="stat-value">{isAdmin ? 'Administrator' : 'Staff'}</div>
          </div>
        </div>
        <div className="stat card">
          <Clock aria-hidden />
          <div>
            <div className="stat-label">Last sign-in</div>
            <div className="stat-value small-value">{lastSignIn ? formatDateTime(lastSignIn) : '—'}</div>
          </div>
        </div>
        {isAdmin && (
          <div className="stat card">
            <Users aria-hidden />
            <div>
              <div className="stat-label">Total users</div>
              <div className="stat-value">{profiles ? profiles.length : '…'}</div>
            </div>
          </div>
        )}
      </section>

      <section aria-label="Modules">
        <h2 className="section-title">Modules</h2>
        <div className="module-grid">
          {cards.map((m) => (
            <Link key={m.path} to={m.path} className="module-card card">
              <div className="module-icon">
                <m.icon size={26} aria-hidden />
              </div>
              <div className="module-text">
                <div className="module-title">{m.label}</div>
                <div className="muted small">{m.description}</div>
              </div>
              <ChevronRight className="module-arrow" aria-hidden />
            </Link>
          ))}
        </div>
      </section>

      <div className="two-col">
        <section className="card">
          <div className="card-header">
            <h2>Recent activity</h2>
            <Link to="/reports" className="link-btn">
              See all
            </Link>
          </div>
          <ActivityList limit={5} nameFor={isAdmin ? nameFor : undefined} />
        </section>
        <InstallAppCard />
      </div>
    </div>
  )
}
