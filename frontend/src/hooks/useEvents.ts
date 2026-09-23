import { useCallback, useEffect, useState } from 'react'
import type { Event, EventQuery } from '../types'
import * as eventsService from '../services/eventsService'
import { errorMessage } from '../services/apiClient'
import { PAGE_SIZE } from '../services/eventsService'

export interface UseEventsResult {
  events: Event[]
  count: number
  totalPages: number
  page: number
  setPage: (page: number) => void
  filters: EventQuery
  updateFilters: (patch: EventQuery) => void
  loading: boolean
  error: string | null
  refresh: () => void
}

/**
 * Fetch the (paginated) event list. Changing filters resets to page 1;
 * `refresh()` re-fetches the current page (e.g. after a CRUD operation).
 *
 * The `loading` flag is turned on by the handlers that trigger a fetch
 * (they always re-run the effect via `reloadKey`), never by the effect
 * itself, so identical re-applications still show feedback.
 */
export function useEvents(): UseEventsResult {
  const [events, setEvents] = useState<Event[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<EventQuery>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let ignore = false
    const run = async () => {
      try {
        const data = await eventsService.list({ ...filters, page })
        if (ignore) return
        setEvents(data.results)
        setCount(data.count)
        setError(null)
      } catch (err) {
        if (ignore) return
        setError(errorMessage(err))
        setEvents([])
      } finally {
        if (!ignore) setLoading(false)
      }
    }
    void run()
    return () => {
      ignore = true
    }
  }, [page, filters, reloadKey])

  const refresh = useCallback(() => {
    setLoading(true)
    setReloadKey((key) => key + 1)
  }, [])

  const updateFilters = useCallback((patch: EventQuery) => {
    setLoading(true)
    setFilters((prev) => ({ ...prev, ...patch }))
    setPage(1)
    setReloadKey((key) => key + 1)
  }, [])

  const goToPage = useCallback((next: number) => {
    setLoading(true)
    setPage(next)
    setReloadKey((key) => key + 1)
  }, [])

  return {
    events,
    count,
    totalPages: Math.max(1, Math.ceil(count / PAGE_SIZE)),
    page,
    setPage: goToPage,
    filters,
    updateFilters,
    loading,
    error,
    refresh,
  }
}
