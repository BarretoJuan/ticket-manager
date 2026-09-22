"""Event repository port."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.entities.event import Event

AVAILABLE = "available"
SOLD_OUT = "sold_out"


@dataclass(frozen=True)
class EventQuery:
    """Filters + pagination input for listing events.

    ``availability`` accepts ``"available"`` (tickets still available) or
    ``"sold_out"`` (no tickets left). ``offset``/``limit`` define the page.
    """

    code: str | None = None
    name: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    availability: str | None = None
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True)
class EventPage:
    """A single page of events plus the total number of matches."""

    items: list[Event]
    total: int


class EventRepository(ABC):
    @abstractmethod
    def create(self, event: Event) -> Event:
        """Persist a new event and return it with DB-assigned timestamps."""

    @abstractmethod
    def get_by_id(self, event_id: UUID) -> Event | None:
        """Return the live (not soft-deleted) event or None."""

    @abstractmethod
    def code_exists(self, code: str) -> bool:
        """True if an event with this code already exists."""

    @abstractmethod
    def list(self, query: EventQuery) -> EventPage:
        """List live events matching ``query``, ordered by date, paginated."""

    @abstractmethod
    def save(self, event: Event) -> Event:
        """Persist changes to an existing event."""

    @abstractmethod
    def soft_delete(self, event_id: UUID) -> None:
        """Set ``deleted_at`` (soft deletion)."""
