/** Bookings API: book tickets for an event. */
import type { Booking } from '../types'
import { apiRequest } from './apiClient'

export function book(
  eventId: string,
  ticketQuantity: number,
): Promise<Booking> {
  return apiRequest<Booking>(`/events/${eventId}/book`, {
    method: 'POST',
    body: { ticket_quantity: ticketQuantity },
  })
}
