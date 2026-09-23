import { useState, type FormEvent } from 'react'
import type { Event } from '../../types'
import { toDatetimeLocal } from '../../utils/format'
import { Button } from '../ui/Button'
import { Field } from '../ui/Field'
import { TextInput } from '../ui/TextInput'

export interface EventFormValues {
  name: string
  code: string
  /** datetime-local value (local wall time). */
  date: string
  total_capacity: number
  ticket_price: number
}

interface EventFormProps {
  event?: Event | null
  submitLabel: string
  busy?: boolean
  onSubmit: (values: EventFormValues) => void
}

const CODE_REGEX = /^EVT-\d{4}-[A-Z]{2}$/

type FormErrors = Partial<Record<keyof EventFormValues, string>>
type FormState = {
  name: string
  code: string
  date: string
  capacity: string
  price: string
}

function initialFormState(event?: Event | null): FormState {
  if (event) {
    return {
      name: event.name,
      code: event.code,
      date: toDatetimeLocal(event.date),
      capacity: String(event.total_capacity),
      price: Number(event.ticket_price).toFixed(2),
    }
  }
  return { name: '', code: '', date: '', capacity: '', price: '' }
}

function validate(state: FormState): FormErrors {
  const errors: FormErrors = {}

  const name = state.name.trim()
  if (!name) errors.name = 'Name is required.'
  else if (name.length < 5 || name.length > 100) {
    errors.name = 'Name must be between 5 and 100 characters.'
  }

  const code = state.code.trim()
  if (!code) errors.code = 'Event code is required.'
  else if (!CODE_REGEX.test(code)) {
    errors.code = 'Code must match EVT-0000-XX (e.g. EVT-2027-MX).'
  }

  if (!state.date) {
    errors.date = 'Event date is required.'
  } else {
    const when = new Date(state.date)
    if (Number.isNaN(when.getTime())) errors.date = 'Invalid date.'
    else if (when.getTime() <= Date.now()) {
      errors.date = 'Event date must be in the future.'
    }
  }

  const capacity = Number(state.capacity)
  if (!state.capacity.trim()) errors.total_capacity = 'Capacity is required.'
  else if (!Number.isInteger(capacity) || capacity < 1) {
    errors.total_capacity = 'Capacity must be a whole number of at least 1.'
  }

  const price = Number(state.price)
  if (!state.price.trim()) errors.ticket_price = 'Price is required.'
  else if (Number.isNaN(price) || price < 0.01) {
    errors.ticket_price = 'Price must be at least 0.01.'
  } else if (Math.abs(price * 100 - Math.round(price * 100)) > 1e-6) {
    errors.ticket_price = 'Price can have at most 2 decimals.'
  }

  return errors
}

/** Create/edit event form with client-side validation mirroring the backend. */
export function EventForm({
  event,
  submitLabel,
  busy = false,
  onSubmit,
}: EventFormProps) {
  const [state, setState] = useState<FormState>(() => initialFormState(event))
  const [errors, setErrors] = useState<FormErrors>({})
  // Adjust state during render when the target event changes (instead of a
  // reset-in-effect), so switching between create/edit never shows stale data.
  const [prevEvent, setPrevEvent] = useState<Event | null | undefined>(event)
  if (prevEvent !== event) {
    setPrevEvent(event)
    setState(initialFormState(event))
    setErrors({})
  }

  const setField = (field: keyof FormState, value: string) => {
    setState((prev) => ({ ...prev, [field]: value }))
    setErrors((prev) => ({ ...prev, [fieldToErrorKey(field)]: undefined }))
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const nextErrors = validate(state)
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return
    onSubmit({
      name: state.name.trim(),
      code: state.code.trim().toUpperCase(),
      date: state.date,
      total_capacity: Number(state.capacity),
      ticket_price: Number(state.price),
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      <Field id="event-name" label="Event name" required error={errors.name}>
        <TextInput
          id="event-name"
          value={state.name}
          onChange={(e) => setField('name', e.target.value)}
          placeholder="Tech Conference 2027"
          maxLength={100}
          required
          invalid={Boolean(errors.name)}
          autoComplete="off"
        />
      </Field>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="event-code"
          label="Event code"
          required
          error={errors.code}
          hint="Format EVT-0000-XX"
        >
          <TextInput
            id="event-code"
            value={state.code}
            onChange={(e) => setField('code', e.target.value.toUpperCase())}
            placeholder="EVT-2027-MX"
            maxLength={12}
            required
            invalid={Boolean(errors.code)}
            autoComplete="off"
          />
        </Field>

        <Field
          id="event-date"
          label="Start date & time"
          required
          error={errors.date}
        >
          <TextInput
            id="event-date"
            type="datetime-local"
            value={state.date}
            onChange={(e) => setField('date', e.target.value)}
            required
            invalid={Boolean(errors.date)}
          />
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          id="event-capacity"
          label="Total capacity"
          required
          error={errors.total_capacity}
        >
          <TextInput
            id="event-capacity"
            type="number"
            inputMode="numeric"
            min={1}
            value={state.capacity}
            onChange={(e) => setField('capacity', e.target.value)}
            placeholder="200"
            required
            invalid={Boolean(errors.total_capacity)}
          />
        </Field>

        <Field
          id="event-price"
          label="Ticket price (USD)"
          required
          error={errors.ticket_price}
        >
          <TextInput
            id="event-price"
            type="number"
            inputMode="decimal"
            min={0.01}
            step="0.01"
            value={state.price}
            onChange={(e) => setField('price', e.target.value)}
            placeholder="25.00"
            required
            invalid={Boolean(errors.ticket_price)}
          />
        </Field>
      </div>

      <Button type="submit" loading={busy} fullWidth>
        {submitLabel}
      </Button>
    </form>
  )
}

function fieldToErrorKey(field: keyof FormState): keyof FormErrors {
  if (field === 'capacity') return 'total_capacity'
  if (field === 'price') return 'ticket_price'
  return field
}
