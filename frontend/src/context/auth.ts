import { createContext } from 'react'
import type { Session } from '../types'

export interface AuthContextValue {
  session: Session | null
  user: Session['user'] | null
  isAdmin: boolean
  isUser: boolean
  login: (email: string, password: string) => Promise<Session['user']>
  register: (email: string, password: string) => Promise<Session['user']>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
