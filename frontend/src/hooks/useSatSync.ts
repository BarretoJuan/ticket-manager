import { useCallback, useEffect, useRef, useState } from 'react'
import type { SatHistory } from '../types'
import * as satService from '../services/satService'
import { ApiError, errorMessage } from '../services/apiClient'
import { useToast } from './useToast'
import { formatDateTime } from '../utils/format'

export interface UseSatSyncResult {
  /** Starting a sync (POST in-flight). */
  starting: boolean
  /** The run being tracked live (polled until a terminal status). */
  current: SatHistory | null
  /** Whether the status of `current` is being polled. */
  polling: boolean
  history: SatHistory[]
  count: number
  page: number
  setPage: (page: number) => void
  historyLoading: boolean
  start: (force: boolean) => Promise<void>
  reloadHistory: () => void
}

const POLL_INTERVAL_MS = 5000

/**
 * SAT automation state: start a sync, poll its status every 5s until it is no
 * longer `processing`, and keep the paginated history list in sync.
 */
export function useSatSync(): UseSatSyncResult {
  const toast = useToast()
  const [starting, setStarting] = useState(false)
  const [current, setCurrent] = useState<SatHistory | null>(null)
  const [polling, setPolling] = useState(false)
  const [history, setHistory] = useState<SatHistory[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let ignore = false
    void (async () => {
      try {
        const data = await satService.listHistory(page)
        if (ignore) return
        setHistory(data.results)
        setCount(data.count)
      } catch (err) {
        if (ignore) return
        toast.error(errorMessage(err))
      } finally {
        if (!ignore) setHistoryLoading(false)
      }
    })()
    return () => {
      ignore = true
    }
  }, [page, reloadKey, toast])

  const reloadHistory = useCallback(() => {
    setHistoryLoading(true)
    setReloadKey((key) => key + 1)
  }, [])

  const goToPage = useCallback((next: number) => {
    setHistoryLoading(true)
    setPage(next)
    setReloadKey((key) => key + 1)
  }, [])

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    setPolling(false)
  }, [])

  // Clear any polling timer on unmount.
  useEffect(() => stopPolling, [stopPolling])

  const poll = useCallback(
    async (historyId: string) => {
      setPolling(true)
      // Returns true while the run is still processing (keep polling).
      const tick = async (): Promise<boolean> => {
        try {
          const status = await satService.getStatus(historyId)
          setCurrent(status)
          if (status.status === 'processing') return true
          stopPolling()
          if (status.status === 'completed') {
            toast.success(
              `SAT automation finished — ${status.record_number} records imported, ${status.omitted_number} omitted.`,
            )
          } else {
            toast.error(
              'SAT automation finished with errors. Check the history for details.',
            )
          }
          setReloadKey((key) => key + 1)
          return false
        } catch (err) {
          stopPolling()
          // A just-started run may 404 momentarily; wait for it to publish.
          const isNotFound = err instanceof ApiError && err.status === 404
          if (isNotFound) {
            toast.info('Waiting for the automation to report…')
            return true
          }
          toast.error(errorMessage(err))
          return false
        }
      }

      const keepPolling = await tick()
      if (keepPolling && timerRef.current === null) {
        timerRef.current = setInterval(async () => {
          const keep = await tick()
          if (!keep) stopPolling()
        }, POLL_INTERVAL_MS)
      }
    },
    [stopPolling, toast],
  )

  const start = useCallback(
    async (force: boolean) => {
      setStarting(true)
      try {
        const result = await satService.startSync(force)
        if ('history_id' in result) {
          setCurrent({
            id: result.history_id,
            status: 'processing',
            started_at: result.started_at,
            completed_at: null,
            user_id: null,
            file_hash: null,
            processing_time: null,
            record_number: 0,
            omitted_number: 0,
          })
          toast.success(
            'SAT automation started. It may take several minutes to finish.',
          )
          void poll(result.history_id)
          reloadHistory()
        } else {
          // 200 skipped — still inside the cooldown window.
          const nextAllowed = result.next_allowed_at
            ? ` Next run allowed at ${formatDateTime(result.next_allowed_at)}.`
            : ''
          toast.info(`Automation skipped: ${result.reason}${nextAllowed}`)
          reloadHistory()
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          toast.error(
            'A SAT automation is already running. Check the history below.',
          )
        } else if (
          err instanceof ApiError &&
          (err.status === 401 || err.status === 403)
        ) {
          toast.error(
            'You need administrator access to run the SAT automation.',
          )
        } else {
          toast.error(errorMessage(err))
        }
      } finally {
        setStarting(false)
      }
    },
    [poll, reloadHistory, toast],
  )

  return {
    starting,
    current,
    polling,
    history,
    count,
    page,
    setPage: goToPage,
    historyLoading,
    start,
    reloadHistory,
  }
}
