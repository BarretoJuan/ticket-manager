"""Event repository port."""

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.event import Event


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
    def list(self, *, code: str | None = None) -> list[Event]:
        """List live events ordered by date, optionally filtered by code."""

    @abstractmethod
    def save(self, event: Event) -> Event:
        """Persist changes to an existing event."""

    @abstractmethod
    def soft_delete(self, event_id: UUID) -> None:
        """Set ``deleted_at`` (soft deletion)."""