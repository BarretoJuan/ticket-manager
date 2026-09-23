import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Role, Session } from '../types'
import * as authService from '../services/authService'
import { setAuthToken, UNAUTHORIZED_EVENT } from '../services/apiClient'
import { AuthContext, type AuthContextValue } from './auth'
import { useToast } from '../hooks/useToast'
import { decodeJwt } from '../utils/jwt'

const STORAGE_KEY = 'ticket-manager.session'

function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<Session>
    if (!parsed.access || !parsed.user?.email || !parsed.user?.id) return null
    return parsed as Session
  } catch {
    return null
  }
}

/** Rebuild the user profile from the JWT claims (role + id) after a login. */
function buildUserFromTokens(
  email: string,
  accessToken: string,
): Session['user'] {
  const claims = decodeJwt(accessToken)
  const role = (claims?.role as Role | undefined) ?? 'USER'
  return { id: String(claims?.user_id ?? ''), email, role }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const toast = useToast()
  const [session, setSession] = useState<Session | null>(() => {
    const loaded = loadSession()
    // Keep the API token store in sync right away: on a full page reload a
    // child effect may fire the first API call before this provider's own
    // mount effect runs, and an unauthenticated first call would 401.
    setAuthToken(loaded?.access ?? null)
    return loaded
  })

  const persist = useCallback((next: Session | null) => {
    setSession(next)
    setAuthToken(next?.access ?? null)
    if (next) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authService.login(email, password)
      const user = buildUserFromTokens(email, tokens.access)
      persist({ access: tokens.access, refresh: tokens.refresh, user })
      return user
    },
    [persist],
  )

  const register = useCallback(
    (email: string, password: string) => authService.register(email, password),
    [],
  )

  const logout = useCallback(() => {
    persist(null)
    toast.info('Signed out.')
  }, [persist, toast])

  // Global 401 handling: expire the session and prompt a re-login.
  useEffect(() => {
    const onUnauthorized = () => {
      persist(null)
      toast.error('Your session has expired. Please sign in again.')
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [persist, toast])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user: session?.user ?? null,
      isAdmin: session?.user.role === 'ADMIN',
      isUser: session?.user.role === 'USER',
      login,
      register,
      logout,
    }),
    [session, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
