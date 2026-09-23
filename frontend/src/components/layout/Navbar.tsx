import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { cn } from '../../utils/cn'
import { IconLogOut, IconTicket } from '../ui/icons'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
    isActive
      ? 'bg-white/10 text-white'
      : 'text-white/65 hover:bg-white/10 hover:text-white',
  )

export function Navbar() {
  const { session, user, isAdmin, logout } = useAuth()
  const navigate = useNavigate()

  if (!session || !user) return null

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="bg-obsidian border-b border-white/10">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-3"
      >
        <div className="flex items-center gap-2">
          <IconTicket className="text-primary h-7 w-7" aria-hidden />
          <NavLink
            to="/"
            className="text-lg font-bold tracking-tight text-white"
          >
            Ticket<span className="text-primary">Manager</span>
          </NavLink>
        </div>

        <div className="flex items-center gap-1">
          {isAdmin ? (
            <>
              <NavLink to="/admin" className={navLinkClass}>
                Events
              </NavLink>
              <NavLink to="/admin/sat" className={navLinkClass}>
                SAT Automation
              </NavLink>
            </>
          ) : (
            <NavLink to="/" className={navLinkClass}>
              Events
            </NavLink>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="min-w-0 text-right">
            <p className="truncate text-sm font-medium text-white">
              {user.email}
            </p>
            <p className="text-primary text-xs">
              {isAdmin ? 'Administrator' : 'Booker'}
            </p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            aria-label="Sign out"
            className="rounded-lg p-2 text-white/65 transition-colors hover:bg-white/10 hover:text-white"
          >
            <IconLogOut className="h-5 w-5" />
          </button>
        </div>
      </nav>
    </header>
  )
}
