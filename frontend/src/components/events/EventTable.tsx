import type { Event } from '../../types'
import { formatDateTime, formatPrice } from '../../utils/format'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { IconPencil, IconTrash } from '../ui/icons'
import { EmptyState } from '../ui/EmptyState'

interface EventTableProps {
  events: Event[]
  onEdit: (event: Event) => void
  onDelete: (event: Event) => void
}

/** Events table (md+) with a stacked-card layout on smaller screens. */
export function EventTable({ events, onEdit, onDelete }: EventTableProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No events yet"
        description="Create your first event with the “New event” button."
      />
    )
  }

  return (
    <>
      {/* Desktop table */}
      <div className="border-navy/15 shadow-card hidden overflow-hidden rounded-2xl border bg-white md:block">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">
            Events — name, date, capacity, price and actions
          </caption>
          <thead className="border-navy/10 bg-offwhite text-muted border-b text-xs tracking-wide uppercase">
            <tr>
              <th scope="col" className="px-4 py-3 font-semibold">
                Event
              </th>
              <th scope="col" className="px-4 py-3 font-semibold">
                Date &amp; time
              </th>
              <th scope="col" className="px-4 py-3 font-semibold">
                Capacity
              </th>
              <th scope="col" className="px-4 py-3 font-semibold">
                Price
              </th>
              <th scope="col" className="px-4 py-3 text-right font-semibold">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-navy/10 divide-y">
            {events.map((event) => (
              <tr key={event.id} className="hover:bg-offwhite/60">
                <td className="px-4 py-3">
                  <p className="text-royal font-medium">{event.name}</p>
                  <p className="text-muted font-mono text-xs">{event.code}</p>
                </td>
                <td className="text-royal px-4 py-3 whitespace-nowrap">
                  {formatDateTime(event.date)}
                </td>
                <td className="px-4 py-3">
                  <span className="text-royal">
                    {event.available_tickets} / {event.total_capacity}
                  </span>{' '}
                  {event.available_tickets === 0 && (
                    <Badge tone="error">Sold out</Badge>
                  )}
                </td>
                <td className="text-royal px-4 py-3 font-medium">
                  {formatPrice(event.ticket_price)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(event)}
                      aria-label={`Edit ${event.name} (${event.code})`}
                      icon={<IconPencil className="h-4 w-4" />}
                    >
                      <span className="sr-only">Edit {event.name}</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(event)}
                      aria-label={`Delete ${event.name} (${event.code})`}
                      icon={<IconTrash className="h-4 w-4 text-red-600" />}
                    >
                      <span className="sr-only">Delete {event.name}</span>
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile stacked cards */}
      <ul className="space-y-3 md:hidden">
        {events.map((event) => (
          <li
            key={event.id}
            className="border-navy/15 shadow-card rounded-2xl border bg-white p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-royal font-medium">{event.name}</p>
                <p className="text-muted font-mono text-xs">{event.code}</p>
              </div>
              {event.available_tickets === 0 && (
                <Badge tone="error">Sold out</Badge>
              )}
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt className="text-muted text-xs">Date &amp; time</dt>
                <dd className="text-royal">{formatDateTime(event.date)}</dd>
              </div>
              <div>
                <dt className="text-muted text-xs">Price</dt>
                <dd className="text-royal font-medium">
                  {formatPrice(event.ticket_price)}
                </dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted text-xs">Capacity</dt>
                <dd className="text-royal">
                  {event.available_tickets} of {event.total_capacity} tickets
                  available
                </dd>
              </div>
            </dl>
            <div className="mt-3 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(event)}
                aria-label={`Edit ${event.name}`}
              >
                Edit
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDelete(event)}
                aria-label={`Delete ${event.name}`}
                className="text-red-700 hover:bg-red-50"
              >
                Delete
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}
