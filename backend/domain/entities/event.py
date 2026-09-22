"""Event entity.

Business rules enforced by :meth:`Event.validate`:
  * ``name`` between 5 and 100 characters.
  * ``code`` matches ``^EVT-\\d{4}-[A-Z]{2}$`` (e.g. EVT-2023-MX).
  * ``date`` must be strictly in the future (UTC aware datetime).
  * ``total_capacity`` > 0, ``available_tickets`` in ``[0, total_capacity]``.
  * ``ticket_price`` > 0.
"""

import re
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from domain.exceptions import (
    EventCapacityError,
    EventCodeFormatError,
    EventNameLengthError,
    EventNotInFutureError,
    EventPriceError,
    InsufficientTicketsError,
)
from domain.utils import utcnow

EVENT_CODE_RE = re.compile(r"^EVT-\d{4}-[A-Z]{2}$")
EVENT_NAME_MIN = 5
EVENT_NAME_MAX = 100


@dataclass(frozen=True)
class Event:
    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    name: str
    code: str
    date: datetime
    total_capacity: int
    available_tickets: int
    ticket_price: Decimal

    def validate(self, now: datetime | None = None) -> None:
        """Validate every business rule. Raises EntityValidationError subclasses."""
        now = now or utcnow()
        if not (EVENT_NAME_MIN <= len(self.name) <= EVENT_NAME_MAX):
            raise EventNameLengthError(
                f"event name must be between {EVENT_NAME_MIN} and {EVENT_NAME_MAX} chars"
            )
        if not EVENT_CODE_RE.match(self.code):
            raise EventCodeFormatError(
                f"event code must match ^EVT-\\d{{4}}-[A-Z]{{2}}$ (got {self.code!r})"
            )
        if self.total_capacity < 1:
            raise EventCapacityError("total_capacity must be greater than 0")
        if self.available_tickets < 0 or self.available_tickets > self.total_capacity:
            raise EventCapacityError(
                "available_tickets must be between 0 and total_capacity"
            )
        if self.ticket_price <= 0:
            raise EventPriceError("ticket_price must be greater than 0")
        # A future date is only required while the event is alive (not soft-deleted).
        if self.deleted_at is None and self.date <= now:
            raise EventNotInFutureError("event date must be in the future")

    def can_book(self, quantity: int) -> bool:
        """Business check: enough available tickets for ``quantity``."""
        return 1 <= quantity <= self.available_tickets

    def with_booking(self, quantity: int) -> "Event":
        """Return a copy with ``quantity`` seats taken (pure, non-atomic).

        Does NOT enforce the max 5 tickets per booking rule; that belongs to
        the ``Booking`` entity. The authoritative decrement happens under a
        database row lock in the booking repository.
        """
        if not self.can_book(quantity):
            raise InsufficientTicketsError(
                f"not enough available tickets (available={self.available_tickets}, requested={quantity})"
            )
        return replace(
            self,
            available_tickets=self.available_tickets - quantity,
            updated_at=utcnow(),
        )