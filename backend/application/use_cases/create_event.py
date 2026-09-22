"""Create an event (admin only is enforced at the presentation layer)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from application.logging_utils import record_log
from domain.entities.event import Event
from domain.entities.log_entry import AuditContext, LogType
from domain.exceptions import EventCodeAlreadyExistsError
from domain.repositories.event_repository import EventRepository
from domain.repositories.log_repository import LogRepository
from domain.utils import ensure_utc, utcnow


class CreateEvent:
    def __init__(
        self,
        event_repository: EventRepository,
        log_repository: LogRepository | None = None,
    ) -> None:
        self.event_repository = event_repository
        self.log_repository = log_repository

    def execute(
        self,
        *,
        name: str,
        code: str,
        date: datetime,
        total_capacity: int,
        ticket_price: Decimal,
        audit: AuditContext | None = None,
    ) -> Event:
        now = utcnow()
        event = Event(
            id=uuid4(),
            created_at=now,
            updated_at=now,
            deleted_at=None,
            name=name.strip(),
            code=code.strip().upper(),
            date=ensure_utc(date),
            total_capacity=total_capacity,
            available_tickets=total_capacity,  # initialized equal to capacity
            ticket_price=ticket_price,
        )
        event.validate(now=now)  # business rules live in the domain

        if self.event_repository.code_exists(event.code):
            raise EventCodeAlreadyExistsError(f"event code {event.code} already exists")

        created = self.event_repository.create(event)
        record_log(
            self.log_repository,
            log_type=LogType.INFO,
            name="event.created",
            content=(
                f"Event {created.code} created: name={created.name}, "
                f"capacity={created.total_capacity}, price={created.ticket_price}"
            ),
            event_id=created.id,
            audit=audit,
        )
        return created