"""Booking entity."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.exceptions import InvalidTicketQuantityError

MIN_TICKETS_PER_BOOKING = 1
MAX_TICKETS_PER_BOOKING = 5


@dataclass(frozen=True)
class Booking:
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    event_id: UUID
    user_id: UUID
    ticket_quantity: int

    def validate(self) -> None:
        if not (
            MIN_TICKETS_PER_BOOKING <= self.ticket_quantity <= MAX_TICKETS_PER_BOOKING
        ):
            raise InvalidTicketQuantityError(
                f"ticket_quantity must be between {MIN_TICKETS_PER_BOOKING} and "
                f"{MAX_TICKETS_PER_BOOKING}, got {self.ticket_quantity}"
            )
