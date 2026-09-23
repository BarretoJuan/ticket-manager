/** Auth API: login and register. */
import type { TokenPair, User } from '../types'
import { apiRequest } from './apiClient'

export function login(email: string, password: string): Promise<TokenPair> {
  return apiRequest<TokenPair>('/login', {
    method: 'POST',
    body: { email, password },
  })
}

export function register(email: string, password: string): Promise<User> {
  return apiRequest<User>('/register', {
    method: 'POST',
    body: { email, password },
  })
}
