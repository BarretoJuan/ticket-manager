/** Decode a JWT payload without a library (claims are base64url JSON). */
export interface JwtClaims {
  user_id?: string
  role?: string
  exp?: number
  [claim: string]: unknown
}

export function decodeJwt(token: string): JwtClaims | null {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      '=',
    )
    return JSON.parse(atob(padded)) as JwtClaims
  } catch {
    return null
  }
}
