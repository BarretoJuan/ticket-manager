import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import type { Role } from '../../types'

interface ProtectedRouteProps {
  /** When set, the signed-in user must have exactly this role. */
  role?: Role
}

/**
 * Route guard rendered as a layout route:
 *  - no session          -> /login (remembers where the user was headed),
 *  - wrong role          -> redirect to that role's home (/admin or /),
 *  - otherwise           -> render the nested routes.
 */
export function ProtectedRoute({ role }: ProtectedRouteProps) {
  const { session, user } = useAuth()
  const location = useLocation()

  if (!session || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === 'ADMIN' ? '/admin' : '/'} replace />
  }

  return <Outlet />
}
