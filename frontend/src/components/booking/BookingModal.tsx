import { useState } from 'react'
import type { Event } from '../../types'
import { formatDateTime, formatPrice } from '../../utils/format'
import { useAuth } from '../../hooks/useAuth'
import { useBooking } from '../../hooks/useBooking'
import { Field } from '../ui/Field'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'

interface BookingModalProps {
  event: Event
  onClose: () => void
  /** Called after a successful booking so the parent can refresh the list. */
  onBooked: () => void
}

const MAX_PER_BOOKING = 5

export function BookingModal({ event, onClose, onBooked }: BookingModalProps) {
  const { user } = useAuth()
  const { book, submitting } = useBooking()
  const [quantity, setQuantity] = useState(1)
  const max = Math.min(MAX_PER_BOOKING, event.available_tickets)

  const increment = () => setQuantity((q) => Math.min(q + 1, max))
  const decrement = () => setQuantity((q) => Math.max(q - 1, 1))

  const handleSubmit = async () => {
    const ok = await book(event.id, quantity)
    if (ok) onBooked()
  }

  return (
    <Modal
      open
      onClose={onClose}
      busy={submitting}
      title="Book tickets"
      description={event.name}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button onClick={() => void handleSubmit()} loading={submitting}>
            Confirm booking
          </Button>
        </>
      }
    >
      <dl className="bg-offwhite rounded-xl p-4 text-sm">
        <div className="grid grid-cols-2 gap-y-2">
          <dt className="text-muted">Date &amp; time</dt>
          <dd className="text-royal text-right">
            <time dateTime={event.date}>{formatDateTime(event.date)}</time>
          </dd>
          <dt className="text-muted">Price per ticket</dt>
          <dd className="text-royal text-right font-medium">
            {formatPrice(event.ticket_price)}
          </dd>
          <dt className="text-muted">Available</dt>
          <dd
            className={`text-right font-medium ${event.available_tickets <= max ? 'text-red-700' : 'text-royal'}`}
          >
            {event.available_tickets} tickets
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <p
          id="ticket-quantity-label"
          className="text-royal mb-1.5 text-sm font-medium"
        >
          Number of tickets
        </p>
        <div
          role="group"
          aria-labelledby="ticket-quantity-label"
          className="flex items-center gap-3"
        >
          <Button
            variant="outline"
            size="sm"
            onClick={decrement}
            disabled={quantity <= 1 || submitting}
            aria-label="Decrease quantity"
            className="px-3 text-lg leading-none"
          >
            −
          </Button>
          <output
            className="text-royal min-w-10 text-center text-lg font-semibold"
            aria-live="polite"
          >
            {quantity}
          </output>
          <Button
            variant="outline"
            size="sm"
            onClick={increment}
            disabled={quantity >= max || submitting}
            aria-label="Increase quantity"
            className="px-3 text-lg leading-none"
          >
            +
          </Button>
          <span className="text-muted text-sm">of {max} max</span>
        </div>
        <p className="text-muted mt-2 text-xs">
          You can book up to {MAX_PER_BOOKING} tickets per booking.
        </p>
      </div>

      <Field
        id="booking-email"
        label="Tickets will be assigned to"
        className="mt-5"
      >
        <div className="bg-offwhite text-royal rounded-lg border border-gray-300 px-3 py-2 text-sm">
          {user?.email ?? '—'}
        </div>
      </Field>
    </Modal>
  )
}
