/**
 * Thin fetch wrapper for the backend API.
 *
 * All HTTP calls go through this module — components and hooks must never
 * call `fetch` directly. It handles:
 *  - the `/api/v1` base URL (proxied by the Vite dev server),
 *  - JSON serialization/parsing,
 *  - the `Authorization: Bearer` header (via the token store),
 *  - normalizing DRF error payloads into a typed `ApiError`,
 *  - dispatching a global "unauthorized" event on every 401 so the Auth
 *    context can expire the session and redirect (other modules can't
 *    re-render React state from here).
 */

export class ApiError extends Error {
  readonly status: number
  readonly detail?: string
  readonly code?: string | null
  readonly fieldErrors?: Record<string, string[]>

  constructor(options: {
    status: number
    message: string
    detail?: string
    code?: string | null
    fieldErrors?: Record<string, string[]>
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.status = options.status
    this.detail = options.detail
    this.code = options.code
    this.fieldErrors = options.fieldErrors
  }
}

const BASE_URL = '/api/v1'

export const UNAUTHORIZED_EVENT = 'ticket-manager:unauthorized'

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  token?: string | null
  params?: object
  signal?: AbortSignal
}

/** Module-level token store so services don't need the token threaded through. */
let currentToken: string | null = null

export function setAuthToken(token: string | null): void {
  currentToken = token
}

export function getAuthToken(): string | null {
  return currentToken
}

function parseErrorPayload(data: unknown): {
  message: string
  detail?: string
  code?: string | null
  fieldErrors?: Record<string, string[]>
} {
  if (typeof data === 'string' && data.length > 0) {
    return { message: data }
  }
  if (data && typeof data === 'object') {
    const obj = data as Record<string, unknown>
    const fieldErrors: Record<string, string[]> = {}
    const fieldMessages: string[] = []

    for (const [key, value] of Object.entries(obj)) {
      if (key === 'detail' || key === 'code' || key === 'non_field_errors')
        continue
      if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
        fieldErrors[key] = value as string[]
        fieldMessages.push(`${key}: ${(value as string[]).join(', ')}`)
      }
    }

    const detail = typeof obj.detail === 'string' ? obj.detail : undefined
    const nonField = Array.isArray(obj.non_field_errors)
      ? (obj.non_field_errors as string[]).join(', ')
      : undefined
    const message = [detail, nonField, ...fieldMessages]
      .filter(Boolean)
      .join(' ')
    return {
      message: (message || 'Request failed.').slice(0, 500),
      detail,
      code: typeof obj.code === 'string' ? obj.code : null,
      fieldErrors,
    }
  }
  return { message: 'Request failed.' }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, token, params, signal } = options

  const url = new URL(`${BASE_URL}${path}`, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    }
  }

  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const authToken = token ?? getAuthToken()
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  let response: Response
  try {
    response = await fetch(url.toString(), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError')
      throw error
    throw new ApiError({
      status: 0,
      message:
        'Network error: the server could not be reached. Please try again.',
    })
  }

  const text = await response.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text) as unknown
    } catch {
      data = text
    }
  }

  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT))
    }

    // Non-JSON bodies (Django debug pages, proxy/gateway errors, …) are not
    // user-facing: render a short generic message instead of spraying raw
    // markup into a toast.
    const contentType = response.headers.get('content-type') ?? ''
    const markupBody =
      !contentType.includes('json') && /^\s*</.test(text.slice(0, 1024))
    if (markupBody) {
      throw new ApiError({
        status: response.status,
        message: `Server error (${response.status}). Please try again.`,
        code: null,
      })
    }

    const parsed = parseErrorPayload(data)
    throw new ApiError({
      status: response.status,
      message: parsed.message,
      detail: parsed.detail,
      code: parsed.code,
      fieldErrors: parsed.fieldErrors,
    })
  }

  return data as T
}

/** Turn any thrown value from a service call into a user-facing message. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 0) return error.message
    return error.detail || error.message || `Request failed (${error.status}).`
  }
  if (error instanceof Error) return error.message
  return 'Something went wrong.'
}
