import type { Event } from '../../types'
import { formatDateTime, formatPrice } from '../../utils/format'
import { Button } from '../ui/Button'
import { IconCalendar, IconTag, IconUsers } from '../ui/icons'

interface EventCardProps {
  event: Event
  onBook: (event: Event) => void
}

/** User-facing event card with availability + booking action. */
export function EventCard({ event, onBook }: EventCardProps) {
  const soldOut = event.available_tickets === 0

  return (
    <article className="border-navy/15 shadow-card hover:shadow-lift flex h-full flex-col rounded-2xl border bg-white p-5 transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-royal text-lg leading-snug font-semibold">
          {event.name}
        </h3>
        <span className="text-muted shrink-0 font-mono text-xs">
          {event.code}
        </span>
      </div>

      <ul className="text-royal mt-4 space-y-2 text-sm">
        <li className="flex items-center gap-2">
          <IconCalendar className="text-primary-dark h-4 w-4 shrink-0" />
          <time dateTime={event.date}>{formatDateTime(event.date)}</time>
        </li>
        <li className="flex items-center gap-2">
          <IconTag className="text-primary-dark h-4 w-4 shrink-0" />
          <span className="font-semibold">
            {formatPrice(event.ticket_price)}
          </span>
          <span className="text-muted">per ticket</span>
        </li>
        <li className="flex items-center gap-2">
          <IconUsers className="text-primary-dark h-4 w-4 shrink-0" />
          {soldOut ? (
            <span className="font-medium text-red-700">No tickets left</span>
          ) : (
            <span>
              <span className="font-medium">{event.available_tickets}</span>{' '}
              <span className="text-muted">
                of {event.total_capacity} tickets available
              </span>
            </span>
          )}
        </li>
      </ul>

      <div className="mt-auto pt-5">
        {soldOut ? (
          <Button variant="outline" fullWidth disabled>
            Sold out
          </Button>
        ) : (
          <Button variant="primary" fullWidth onClick={() => onBook(event)}>
            Book tickets
          </Button>
        )}
      </div>
    </article>
  )
}
