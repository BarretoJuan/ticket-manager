import { useCallback, useState } from 'react'
import * as bookingsService from '../services/bookingsService'
import { errorMessage } from '../services/apiClient'
import { useAuth } from './useAuth'
import { useToast } from './useToast'

/**
 * Book tickets. Enforces the business rule that only regular users can book
 * (admins manage events, they don't purchase tickets), then calls the API.
 * Returns true on success so the caller can refresh/close modals.
 */
export function useBooking() {
  const { user } = useAuth()
  const toast = useToast()
  const [submitting, setSubmitting] = useState(false)

  const book = useCallback(
    async (eventId: string, quantity: number): Promise<boolean> => {
      if (user?.role !== 'USER') {
        toast.error(
          'Only regular users can book tickets. Please sign in with a user account.',
        )
        return false
      }
      setSubmitting(true)
      try {
        await bookingsService.book(eventId, quantity)
        toast.success(
          `Booking confirmed — ${quantity} ticket${quantity === 1 ? '' : 's'}. A confirmation email is on its way.`,
        )
        return true
      } catch (err) {
        toast.error(errorMessage(err))
        return false
      } finally {
        setSubmitting(false)
      }
    },
    [user, toast],
  )

  return { book, submitting }
}
