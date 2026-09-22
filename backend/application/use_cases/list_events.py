"""List events."""

from domain.entities.event import Event
from domain.repositories.event_repository import EventRepository


class ListEvents:
    def __init__(self, event_repository: EventRepository) -> None:
        self.event_repository = event_repository

    def execute(self, *, code: str | None = None) -> list[Event]:
        return self.event_repository.list(code=code)