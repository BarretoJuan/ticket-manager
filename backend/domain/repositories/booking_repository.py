"""Booking repository port."""

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.booking import Booking
from domain.exceptions import InsufficientTicketsError


class BookingRepository(ABC):

    @abstractmethod
    def create_booking_atomic(
        self, *, event_id: UUID, user_id: UUID, quantity: int
    ) -> Booking:
        """Atomically book tickets for an event.

        Implementations MUST run inside a database transaction, acquire a
        pessimistic row-level lock on the event (``SELECT ... FOR UPDATE``),
        re-validate the available capacity under that lock and decrement
        ``available_tickets`` before inserting the booking. If the capacity is
        exhausted (even from a race), raise :class:`InsufficientTicketsError`.
        """