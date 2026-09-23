/** ISO 8601 UTC datetime string, e.g. "2027-06-15T09:00:00Z". */
export type DateTimeString = string

export type Role = 'ADMIN' | 'USER'

export interface User {
  id: string
  email: string
  role: Role
}

export interface TokenPair {
  access: string
  refresh: string
}

/** A persisted authenticated session (tokens + the signed-in user). */
export interface Session {
  access: string
  refresh: string
  user: User
}

export interface Event {
  id: string
  created_at: DateTimeString
  updated_at: DateTimeString
  deleted_at: DateTimeString | null
  name: string
  /** Must match ^EVT-\d{4}-[A-Z]{2}$ (e.g. EVT-2027-MX). */
  code: string
  /** Event start date/time (UTC). */
  date: DateTimeString
  total_capacity: number
  available_tickets: number
  /** Decimal as a string, e.g. "250.00". */
  ticket_price: string
}

export interface EventPayload {
  name: string
  code: string
  date: DateTimeString
  total_capacity: number
  ticket_price: string
}

export type EventAvailability = 'available' | 'sold_out'

export interface EventQuery {
  page?: number
  code?: string
  name?: string
  /** YYYY-MM-DD */
  date_from?: string
  /** YYYY-MM-DD */
  date_to?: string
  availability?: EventAvailability
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Booking {
  id: string
  created_at: DateTimeString
  event_id: string
  user_id: string
  ticket_quantity: number
}

export type SatStatus = 'processing' | 'completed' | 'error'

export interface SatHistory {
  id: string
  status: SatStatus
  started_at: DateTimeString
  completed_at: DateTimeString | null
  user_id: string | null
  file_hash: string | null
  processing_time: number | null
  /** Rows imported into sat_cancelados. */
  record_number: number
  /** Rows skipped (invalid or already stored). */
  omitted_number: number
}

export interface SatStarted {
  history_id: string
  status: string
  started_at: DateTimeString
  force: boolean
}

export interface SatSkipped {
  status: 'skipped'
  reason: string
  next_allowed_at: DateTimeString | null
  last_sync: SatHistory | null
}
