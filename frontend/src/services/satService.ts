/** SAT open-data sync API (art. 69 CFF "Cancelados") — admin only. */
import type { Paginated, SatHistory, SatSkipped, SatStarted } from '../types'
import { apiRequest } from './apiClient'

/**
 * Start a sync. Resolves to `SatStarted` (202) when the run was started or
 * `SatSkipped` (200) when a successful run is still inside the cooldown.
 * Throws ApiError 409 when another sync is already running.
 */
export function startSync(force = false): Promise<SatStarted | SatSkipped> {
  return apiRequest<SatStarted | SatSkipped>('/sat/sync', {
    method: 'POST',
    params: { force },
  })
}

/** Poll the status of a sync run. */
export function getStatus(historyId: string): Promise<SatHistory> {
  return apiRequest<SatHistory>(`/sat/sync/${historyId}`)
}

/** List the last processed files — 20 per page, newest first. */
export function listHistory(page = 1): Promise<Paginated<SatHistory>> {
  return apiRequest<Paginated<SatHistory>>('/sat/history', { params: { page } })
}
