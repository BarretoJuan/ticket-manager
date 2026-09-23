/** Events API: list/create/update/soft-delete. */
import type { Event, EventPayload, EventQuery, Paginated } from '../types'
import { apiRequest } from './apiClient'

export const PAGE_SIZE = 20

export function list(params: EventQuery = {}): Promise<Paginated<Event>> {
  return apiRequest<Paginated<Event>>('/events', { params })
}

export function create(payload: EventPayload): Promise<Event> {
  return apiRequest<Event>('/events', { method: 'POST', body: payload })
}

export function update(
  id: string,
  payload: Partial<EventPayload>,
): Promise<Event> {
  return apiRequest<Event>(`/events/${id}`, { method: 'PATCH', body: payload })
}

export function remove(id: string): Promise<void> {
  return apiRequest<void>(`/events/${id}`, { method: 'DELETE' })
}
