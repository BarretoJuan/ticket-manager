import { useState, type FormEvent } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useEvents } from '../hooks/useEvents'
import type { Event, EventAvailability } from '../types'
import { Button } from '../components/ui/Button'
import { Field } from '../components/ui/Field'
import { Pagination } from '../components/ui/Pagination'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import { TextInput } from '../components/ui/TextInput'
import { EmptyState } from '../components/ui/EmptyState'
import { EventCard } from '../components/events/EventCard'
import { BookingModal } from '../components/booking/BookingModal'
import {
  IconAlertCircle,
  IconCalendar,
  IconSearch,
} from '../components/ui/icons'
import { cn } from '../utils/cn'

type AvailabilityFilter = '' | EventAvailability

export function UserEventsPage() {
  const { user } = useAuth()
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

  const [booking, setBooking] = useState<Event | null>(null)
  const [search, setSearch] = useState('')
  const [availability, setAvailability] = useState<AvailabilityFilter>('')

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

  const hasFilters = Boolean(search.trim() || availability)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-royal text-2xl font-bold sm:text-3xl">
          Hello{user?.email ? `, ${user.email.split('@')[0]}` : ''} 👋
        </h1>
        <p className="text-muted mt-1 text-sm">
          Upcoming events with live availability. Book your tickets in seconds.
        </p>
      </header>

      {/* Filters */}
      <form
        onSubmit={applyFilters}
        className="border-navy/15 shadow-card rounded-2xl border bg-white p-4"
        aria-label="Filter events"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <Field id="user-search" label="Search by name" className="flex-1">
            <div className="relative">
              <IconSearch className="text-muted pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
              <TextInput
                id="user-search"
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="e.g. Tech Conference"
                className="pl-9"
              />
            </div>
          </Field>
          <Field
            id="user-availability"
            label="Availability"
            className="sm:w-48"
          >
            <Select
              id="user-availability"
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

      {/* Event grid */}
      <section aria-label="Available events">
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
            className={cn(
              'border-navy/15 text-muted flex items-center justify-center gap-2 rounded-2xl border bg-white py-16',
            )}
            aria-live="polite"
          >
            <Spinner className="h-5 w-5" />
            <span>Loading events…</span>
          </div>
        ) : events.length === 0 ? (
          <EmptyState
            icon={<IconCalendar className="h-8 w-8" />}
            title="No events match"
            description={
              hasFilters
                ? 'Try adjusting your search or filters.'
                : 'There are no upcoming events right now. Check back soon!'
            }
            action={
              hasFilters ? (
                <Button variant="outline" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {events.map((event) => (
              <EventCard key={event.id} event={event} onBook={setBooking} />
            ))}
          </div>
        )}
      </section>

      {!loading && events.length > 0 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          totalItems={count}
          onPageChange={setPage}
        />
      )}

      {booking && (
        <BookingModal
          event={booking}
          onClose={() => setBooking(null)}
          onBooked={() => {
            setBooking(null)
            refresh()
          }}
        />
      )}
    </div>
  )
}
