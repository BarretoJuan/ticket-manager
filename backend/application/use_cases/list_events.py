"""List events."""

from domain.repositories.event_repository import EventPage, EventQuery, EventRepository


class ListEvents:
    def __init__(self, event_repository: EventRepository) -> None:
        self.event_repository = event_repository

    def execute(self, *, query: EventQuery) -> EventPage:
        return self.event_repository.list(query=query)
