"""Soft-delete an event (admin only is enforced at the presentation layer)."""

from uuid import UUID

from application.logging_utils import record_log
from domain.entities.log_entry import AuditContext, LogType
from domain.exceptions import EventNotFoundError
from domain.repositories.event_repository import EventRepository
from domain.repositories.log_repository import LogRepository


class DeleteEvent:
    def __init__(
        self,
        event_repository: EventRepository,
        log_repository: LogRepository | None = None,
    ) -> None:
        self.event_repository = event_repository
        self.log_repository = log_repository

    def execute(self, *, event_id: UUID, audit: AuditContext | None = None) -> None:
        event = self.event_repository.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError("event not found")

        self.event_repository.soft_delete(event_id)
        record_log(
            self.log_repository,
            log_type=LogType.INFO,
            name="event.deleted",
            content=f"Event {event.code} soft-deleted",
            event_id=event_id,
            audit=audit,
        )