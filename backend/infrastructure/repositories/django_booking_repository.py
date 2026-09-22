"""Django implementation of the BookingRepository port.

``create_booking_atomic`` guarantees there are never more tickets sold than the
event capacity, even under race conditions:

  1. Opens a database transaction (``transaction.atomic()``).
  2. Locks the event row with ``SELECT ... FOR UPDATE`` (``select_for_update()``).
  3. Re-validates the available capacity under the lock.
  4. Decrements ``available_tickets`` and inserts the booking.
  5. Commits (or rolls everything back if the capacity check fails).

Concurrent requests that target the same event are serialized by the row lock,
so the capacity is never oversold.
"""

from uuid import UUID

from django.db import transaction

from domain.entities.booking import Booking
from domain.exceptions import EventNotFoundError, InsufficientTicketsError
from domain.repositories.booking_repository import BookingRepository

from infrastructure.orm.models import BookingORM, EventORM
from infrastructure.repositories.mappers import booking_orm_to_domain


class DjangoBookingRepository(BookingRepository):

    def create_booking_atomic(
        self, *, event_id: UUID, user_id: UUID, quantity: int
    ) -> Booking:
        with transaction.atomic():
            # Pessimistic row-level lock on the event row.
            event_row = (
                EventORM.objects.select_for_update()
                .filter(pk=event_id, deleted_at__isnull=True)
                .first()
            )
            if event_row is None:
                raise EventNotFoundError("event not found")

            # Authoritative capacity check, executed while holding the row lock.
            if event_row.available_tickets < quantity:
                raise InsufficientTicketsError(
                    f"not enough available tickets "
                    f"(available={event_row.available_tickets}, requested={quantity})"
                )

            event_row.available_tickets -= quantity
            event_row.save(update_fields=["available_tickets", "updated_at"])

            booking = BookingORM.objects.create(
                event_id=event_id,
                user_id=user_id,
                ticket_quantity=quantity,
            )
            booking.refresh_from_db()
            return booking_orm_to_domain(booking)
