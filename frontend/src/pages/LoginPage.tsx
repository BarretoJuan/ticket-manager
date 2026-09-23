import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { errorMessage } from '../services/apiClient'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { TextInput } from '../components/ui/TextInput'
import {
  IconAlertCircle,
  IconCheckCircle,
  IconTicket,
} from '../components/ui/icons'
import { cn } from '../utils/cn'

type Mode = 'login' | 'register'

const DEMO_ACCOUNTS = [
  { label: 'Admin', email: 'admin@example.com', password: 'Admin12345!' },
  { label: 'User', email: 'alice@example.com', password: 'Demo12345!' },
]

export function LoginPage() {
  const { session, login, register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Already signed in? Go straight to the right area.
  if (session?.user) {
    return (
      <Navigate to={session.user.role === 'ADMIN' ? '/admin' : '/'} replace />
    )
  }

  const from = (location.state as { from?: string } | null)?.from

  const switchMode = (next: Mode) => {
    setMode(next)
    setError(null)
    setPassword('')
    setConfirmPassword('')
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    if (mode === 'register' && password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      if (mode === 'login') {
        const user = await login(email.trim(), password)
        toast.success(`Welcome back, ${user.email}`)
        const destination = user.role === 'ADMIN' ? '/admin' : (from ?? '/')
        navigate(destination, { replace: true })
      } else {
        await register(email.trim(), password)
        toast.success('Account created — sign in to continue.')
        switchMode('login')
      }
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand hero panel */}
      <aside className="from-ocean via-navy to-obsidian hidden w-1/2 flex-col justify-between bg-gradient-to-br p-12 text-white lg:flex">
        <div className="flex items-center gap-2">
          <IconTicket className="text-primary h-8 w-8" />
          <span className="text-xl font-bold">
            Ticket<span className="text-primary">Manager</span>
          </span>
        </div>
        <div className="max-w-md">
          <h1 className="text-4xl leading-tight font-bold">
            Buy tickets for the events you love
          </h1>
          <ul className="mt-6 space-y-3 text-white/80">
            <li className="flex items-center gap-2">
              <IconCheckCircle className="text-primary h-5 w-5 shrink-0" />
              Browse upcoming events with live availability
            </li>
            <li className="flex items-center gap-2">
              <IconCheckCircle className="text-primary h-5 w-5 shrink-0" />
              Book 1–5 tickets and get a confirmation e-mail
            </li>
            <li className="flex items-center gap-2">
              <IconCheckCircle className="text-primary h-5 w-5 shrink-0" />
              Admins manage events and SAT automation
            </li>
          </ul>
        </div>
        <p className="text-sm text-white/50">
          © {new Date().getFullYear()} Ticket Manager
        </p>
      </aside>

      {/* Form panel */}
      <main className="bg-offwhite flex flex-1 items-center justify-center px-4 py-10">
        <div className="border-navy/15 shadow-card w-full max-w-md rounded-2xl border bg-white p-8">
          <div className="flex items-center gap-2 lg:hidden">
            <IconTicket className="text-primary-dark h-7 w-7" />
            <span className="text-royal text-lg font-bold">
              Ticket<span className="text-primary-dark">Manager</span>
            </span>
          </div>

          <h2 className="text-royal mt-4 text-2xl font-bold">
            {mode === 'login' ? 'Sign in' : 'Create an account'}
          </h2>
          <p className="text-muted mt-1 text-sm">
            {mode === 'login'
              ? 'Access your events and bookings.'
              : 'Free for everyone — you can start booking right away.'}
          </p>

          {/* Mode toggle */}
          <div
            role="tablist"
            aria-label="Authentication mode"
            className="bg-offwhite mt-6 grid grid-cols-2 rounded-xl p-1"
          >
            {(['login', 'register'] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={mode === value}
                onClick={() => switchMode(value)}
                className={cn(
                  'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
                  mode === value
                    ? 'text-royal ring-navy/15 bg-white shadow-sm ring-1'
                    : 'text-muted hover:text-royal',
                )}
              >
                {value === 'login' ? 'Sign in' : 'Register'}
              </button>
            ))}
          </div>

          {error && (
            <div
              role="alert"
              className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
            >
              <IconAlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-4">
            <Field id="login-email" label="Email" required>
              <TextInput
                id="login-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </Field>

            <Field
              id="login-password"
              label="Password"
              required
              hint={mode === 'register' ? 'At least 8 characters.' : undefined}
            >
              <TextInput
                id="login-password"
                type="password"
                autoComplete={
                  mode === 'login' ? 'current-password' : 'new-password'
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={mode === 'register' ? 8 : undefined}
              />
            </Field>

            {mode === 'register' && (
              <Field id="login-confirm" label="Confirm password" required>
                <TextInput
                  id="login-confirm"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={8}
                />
              </Field>
            )}

            <Button type="submit" fullWidth size="lg" loading={submitting}>
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </Button>
          </form>

          {/* Demo credentials */}
          <div className="border-navy/15 bg-offwhite mt-6 rounded-xl border p-4">
            <p className="text-muted text-xs font-semibold tracking-wide uppercase">
              Demo accounts
            </p>
            <ul className="text-royal mt-2 space-y-1.5 text-xs">
              {DEMO_ACCOUNTS.map((account) => (
                <li
                  key={account.email}
                  className="flex flex-wrap gap-x-2 gap-y-0.5"
                >
                  <span className="font-semibold">{account.label}:</span>
                  <span>{account.email}</span>
                  <span className="text-muted font-mono">
                    {account.password}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </main>
    </div>
  )
}
