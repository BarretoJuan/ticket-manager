"""Book tickets for an event — guaranteed no overbooking even under races.

The authoritative capacity check + decrement happen atomically inside
``BookingRepository.create_booking_atomic`` which uses PostgreSQL pessimistic
row-level locking (``SELECT ... FOR UPDATE``) inside a database transaction.
"""

import logging
from uuid import UUID, uuid4

from application.logging_utils import record_log
from application.services.booking_notifier import BookingNotifier
from domain.entities.booking import Booking
from domain.entities.event import Event
from domain.entities.log_entry import AuditContext, LogType
from domain.exceptions import EventNotFoundError, InsufficientTicketsError
from domain.repositories.booking_repository import BookingRepository
from domain.repositories.event_repository import EventRepository
from domain.repositories.log_repository import LogRepository
from domain.utils import utcnow

logger = logging.getLogger("application")


class BookTicket:
    def __init__(
        self,
        booking_repository: BookingRepository,
        event_repository: EventRepository,
        log_repository: LogRepository | None = None,
        notifier: BookingNotifier | None = None,
    ) -> None:
        self.booking_repository = booking_repository
        self.event_repository = event_repository
        self.log_repository = log_repository
        self.notifier = notifier

    def execute(
        self,
        *,
        event_id: UUID,
        user_id: UUID,
        quantity: int,
        audit: AuditContext | None = None,
    ) -> Booking:
        # Domain validation: quantity between 1 and 5.
        booking = Booking(
            id=uuid4(),
            created_at=utcnow(),
            updated_at=utcnow(),
            deleted_at=None,
            event_id=event_id,
            user_id=user_id,
            ticket_quantity=quantity,
        )
        booking.validate()

        # Early, cheap business check to fail fast with a clear message.
        event = self.event_repository.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError("event not found")

        try:
            if not event.can_book(quantity):
                raise InsufficientTicketsError(
                    f"not enough available tickets "
                    f"(available={event.available_tickets}, requested={quantity})"
                )
            # Atomic: row lock + authoritative re-check + decrement + insert.
            created = self.booking_repository.create_booking_atomic(
                event_id=event_id,
                user_id=user_id,
                quantity=quantity,
            )
        except InsufficientTicketsError:
            record_log(
                self.log_repository,
                log_type=LogType.WARNING,
                name="booking.rejected",
                content=(
                    f"Booking rejected: event {event_id} lacks capacity "
                    f"for {quantity} tickets"
                ),
                user_id=user_id,
                event_id=event_id,
                audit=audit,
            )
            raise

        record_log(
            self.log_repository,
            log_type=LogType.INFO,
            name="booking.created",
            content=(
                f"Booking created: {created.ticket_quantity} ticket(s) "
                f"for event {event_id}"
            ),
            user_id=user_id,
            event_id=event_id,
            audit=audit,
        )
        self._send_confirmation(created, event, user_id, audit)
        return created

    def _send_confirmation(
        self,
        booking: Booking,
        event: Event,
        user_id: UUID,
        audit: AuditContext | None,
    ) -> None:
        """Send the confirmation e-mail; failures must never fail a booking."""
        if self.notifier is None:
            return
        try:
            self.notifier.send_booking_confirmation(
                booking=booking, event=event, user_id=user_id
            )
        except Exception:
            logger.exception(
                "failed to send booking confirmation for booking %s", booking.id
            )
            record_log(
                self.log_repository,
                log_type=LogType.WARNING,
                name="booking.email_failed",
                content=(
                    f"Confirmation e-mail failed for booking {booking.id} "
                    f"(event {event.id}, user {user_id})"
                ),
                user_id=user_id,
                event_id=event.id,
                audit=audit,
            )
