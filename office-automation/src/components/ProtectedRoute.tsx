import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import type { Role } from '../lib/types'
import { FullPageMessage, LoadingScreen } from './FullPageMessage'

/**
 * Only lets logged-in users through. If `roles` is given, the user must
 * also have one of those roles (e.g. admin-only pages).
 *
 * Note: this only hides screens. The real protection is the database
 * security (Row Level Security), which the server always enforces.
 */
export function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { session, profile, loading, profileError, signOut } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingScreen />
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />

  if (!profile) {
    return (
      <FullPageMessage title="Account not ready">
        <p className="muted">{profileError ?? 'Your profile could not be loaded.'}</p>
        <button type="button" className="btn btn-secondary" onClick={() => void signOut()}>
          Sign out
        </button>
      </FullPageMessage>
    )
  }

  if (roles && !roles.includes(profile.role)) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
