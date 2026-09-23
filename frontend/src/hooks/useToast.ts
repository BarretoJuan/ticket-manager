import { useCallback, useContext, useMemo } from 'react'
import { ToastContext } from '../context/toast'

/** Convenience wrapper: toast.success(...) / toast.error(...) / toast.info(...). */
export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }

  // `ctx.notify` is referentially stable (provider useCallback rooted at an
  // empty-deps `dismiss`), so this API is stable across renders. Hooks are
  // allowed to put `toast` in effect/useCallback dependency arrays without
  // accidentally re-running on every render.
  const notify = ctx.notify

  const success = useCallback(
    (message: string) => notify('success', message),
    [notify],
  )
  const error = useCallback(
    (message: string) => notify('error', message),
    [notify],
  )
  const info = useCallback(
    (message: string) => notify('info', message),
    [notify],
  )

  return useMemo(
    () => ({ success, error, info, notify }),
    [success, error, info, notify],
  )
}

export type { ToastType } from '../context/toast'
