import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useEvents } from '../hooks/useEvents'
import { useToast } from '../hooks/useToast'
import * as eventsService from '../services/eventsService'
import { errorMessage } from '../services/apiClient'
import type { Event, EventPayload } from '../types'
import { fromDatetimeLocal } from '../utils/format'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { Modal } from '../components/ui/Modal'
import { Pagination } from '../components/ui/Pagination'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import { TextInput } from '../components/ui/TextInput'
import {
  IconAlertCircle,
  IconPlus,
  IconRobot,
  IconSearch,
} from '../components/ui/icons'
import { EventForm, type EventFormValues } from '../components/events/EventForm'
import { EventTable } from '../components/events/EventTable'

type AvailabilityFilter = '' | 'available' | 'sold_out'

export function AdminEventsPage() {
  const toast = useToast()
  const {
    events,
    count,
    totalPages,
    page,
    setPage,
    updateFilters,
    loading,
    error,
    refresh,
  } = useEvents()

  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Event | null>(null)
  const [deleting, setDeleting] = useState<Event | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Local filter inputs (applied explicitly to avoid a request per keystroke).
  const [search, setSearch] = useState('')
  const [availability, setAvailability] = useState<AvailabilityFilter>('')

  const openCreate = () => {
    setEditing(null)
    setFormOpen(true)
  }

  const openEdit = (event: Event) => {
    setEditing(event)
    setFormOpen(true)
  }

  const applyFilters = (event?: FormEvent) => {
    event?.preventDefault()
    updateFilters({
      name: search.trim() || undefined,
      availability: availability || undefined,
    })
  }

  const clearFilters = () => {
    setSearch('')
    setAvailability('')
    updateFilters({ name: undefined, availability: undefined })
  }

  const handleSubmit = async (values: EventFormValues) => {
    setSubmitting(true)
    try {
      const payload: EventPayload = {
        name: values.name,
        code: values.code.toUpperCase(),
        date: fromDatetimeLocal(values.date),
        total_capacity: values.total_capacity,
        ticket_price: values.ticket_price.toFixed(2),
      }
      if (editing) {
        await eventsService.update(editing.id, payload)
        toast.success(`Event "${payload.name}" updated.`)
      } else {
        await eventsService.create(payload)
        toast.success(`Event "${payload.name}" created.`)
      }
      setFormOpen(false)
      await refresh()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!deleting) return
    setSubmitting(true)
    try {
      await eventsService.remove(deleting.id)
      toast.success(`Event "${deleting.name}" deleted.`)
      setDeleting(null)
      await refresh()
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const hasFilters = Boolean(search.trim() || availability)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-royal text-2xl font-bold sm:text-3xl">
            Events management
          </h1>
          <p className="text-muted mt-1 text-sm">
            Create, edit and remove events. Changes apply immediately.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" asChild>
            <Link to="/admin/sat" className="inline-flex items-center gap-2">
              <IconRobot className="h-4 w-4" />
              SAT Automation
            </Link>
          </Button>
          <Button
            variant="primary"
            icon={<IconPlus className="h-4 w-4" />}
            onClick={openCreate}
          >
            New event
          </Button>
        </div>
      </header>

      {/* Filters */}
      <form
        onSubmit={applyFilters}
        className="border-navy/15 shadow-card rounded-2xl border bg-white p-4"
        aria-label="Filter events"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field id="admin-search" label="Search by name" className="flex-1">
            <div className="relative">
              <IconSearch className="text-muted pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
              <TextInput
                id="admin-search"
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="e.g. Tech Conference"
                className="pl-9"
              />
            </div>
          </Field>
          <Field
            id="admin-availability"
            label="Availability"
            className="sm:w-48"
          >
            <Select
              id="admin-availability"
              value={availability}
              onChange={(e) =>
                setAvailability(e.target.value as AvailabilityFilter)
              }
            >
              <option value="">All</option>
              <option value="available">Available</option>
              <option value="sold_out">Sold out</option>
            </Select>
          </Field>
          <div className="flex gap-2">
            <Button type="submit" variant="secondary">
              Apply
            </Button>
            {hasFilters && (
              <Button type="button" variant="ghost" onClick={clearFilters}>
                Clear
              </Button>
            )}
          </div>
        </div>
      </form>

      {/* List */}
      <section aria-label="Events list">
        {error && (
          <div
            role="alert"
            className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          >
            <span className="flex items-center gap-2">
              <IconAlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </span>
            <Button variant="outline" size="sm" onClick={() => void refresh()}>
              Try again
            </Button>
          </div>
        )}

        {loading ? (
          <div
            className="border-navy/15 text-muted flex items-center justify-center gap-2 rounded-2xl border bg-white py-16"
            aria-live="polite"
          >
            <Spinner className="h-5 w-5" />
            <span>Loading events…</span>
          </div>
        ) : (
          <>
            {!hasFilters && !error && (
              <p className="text-muted mb-3 text-sm" aria-live="polite">
                {count === 0
                  ? 'No upcoming events.'
                  : `${count} upcoming event${count === 1 ? '' : 's'}.`}
              </p>
            )}
            <EventTable
              events={events}
              onEdit={openEdit}
              onDelete={setDeleting}
            />
            <Pagination
              page={page}
              totalPages={totalPages}
              totalItems={count}
              onPageChange={setPage}
              className="mt-4"
            />
          </>
        )}
      </section>

      {/* Create / edit modal */}
      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? 'Edit event' : 'New event'}
        description={
          editing
            ? `${editing.name} · ${editing.code}`
            : 'All fields are required.'
        }
        busy={submitting}
      >
        <EventForm
          key={editing?.id ?? 'new'}
          event={editing}
          submitLabel={editing ? 'Save changes' : 'Create event'}
          busy={submitting}
          onSubmit={handleSubmit}
        />
      </Modal>

      {/* Delete confirmation modal */}
      <Modal
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        title="Delete event"
        description={
          deleting
            ? `"${deleting.name}" will be hidden from the catalog. This cannot be undone.`
            : undefined
        }
        busy={submitting}
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => setDeleting(null)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => void handleDelete()}
              loading={submitting}
            >
              Delete event
            </Button>
          </>
        }
      >
        {deleting ? (
          <div className="flex items-center gap-2 rounded-xl bg-red-50 p-3 text-sm text-red-800">
            <IconAlertCircle className="h-5 w-5 shrink-0" />
            <span>
              This will soft-delete the event and hide it from the catalog.
            </span>
          </div>
        ) : null}
      </Modal>
    </div>
  )
}
