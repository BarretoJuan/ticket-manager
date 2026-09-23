const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

const dateTime = new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const dateOnly = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' })

/**
 * Format a ticket price (backend sends decimals as a string, e.g. "250.00")
 * as USD currency.
 */
export function formatPrice(value: string | number): string {
  const amount = Number(value)
  return Number.isFinite(amount) ? currency.format(amount) : String(value)
}

/** Format a UTC ISO datetime in the browser's local timezone. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : dateTime.format(date)
}

/** Format a UTC ISO datetime as a local date only. */
export function formatDate(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : dateOnly.format(date)
}

/** Seconds -> human duration, e.g. "3m 25s" or "12.4s". */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  const total = Math.round(seconds)
  if (total < 60) return `${total}s`
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  if (minutes < 60) return `${minutes}m ${rest}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m ${rest}s`
}

/**
 * Convert a UTC ISO datetime to the value expected by a
 * <input type="datetime-local"> (YYYY-MM-DDTHH:mm in local time).
 */
export function toDatetimeLocal(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/**
 * Convert a `<input type="datetime-local">` value (local wall time) to a UTC
 * ISO datetime string for the API payload.
 */
export function fromDatetimeLocal(value: string): string {
  return new Date(value).toISOString()
}

/** Shorten a long identifier/hash for display: "ab34cd12…". */
export function truncateMiddle(
  value: string | null | undefined,
  keep = 8,
): string {
  if (!value) return '—'
  return value.length > keep * 2 + 1
    ? `${value.slice(0, keep)}…${value.slice(-keep)}`
    : value
}
