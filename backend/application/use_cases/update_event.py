"""Update an event (admin only is enforced at the presentation layer)."""

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from application.logging_utils import record_log
from domain.entities.event import Event
from domain.entities.log_entry import AuditContext, LogType
from domain.exceptions import (
    EventCapacityError,
    EventCodeAlreadyExistsError,
    EventNotFoundError,
)
from domain.repositories.event_repository import EventRepository
from domain.repositories.log_repository import LogRepository
from domain.utils import ensure_utc, utcnow


class UpdateEvent:
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
        event_id: UUID,
        name: str | None = None,
        code: str | None = None,
        date: datetime | None = None,
        total_capacity: int | None = None,
        ticket_price: Decimal | None = None,
        audit: AuditContext | None = None,
    ) -> Event:
        event = self.event_repository.get_by_id(event_id)
        if event is None:
            raise EventNotFoundError("event not found")

        now = utcnow()

        # Capacity handling: booked seats can never exceed the new capacity.
        if total_capacity is not None:
            sold = event.total_capacity - event.available_tickets
            if total_capacity < sold:
                raise EventCapacityError(
                    "total_capacity cannot be lower than the tickets already booked "
                    f"({sold})"
                )
            new_total_capacity = total_capacity
            new_available_tickets = total_capacity - sold
        else:
            new_total_capacity = event.total_capacity
            new_available_tickets = event.available_tickets

        updated = replace(
            event,
            name=name.strip() if name is not None else event.name,
            code=code.strip().upper() if code is not None else event.code,
            date=ensure_utc(date) if date is not None else event.date,
            total_capacity=new_total_capacity,
            available_tickets=new_available_tickets,
            ticket_price=ticket_price if ticket_price is not None else event.ticket_price,
            updated_at=now,
        )
        updated.validate(now=now)  # business rules live in the domain

        if code is not None and code.upper().strip() != event.code and self.event_repository.code_exists(code.upper().strip()):
            raise EventCodeAlreadyExistsError(f"event code {code.upper().strip()} already exists")

        saved = self.event_repository.save(updated)
        record_log(
            self.log_repository,
            log_type=LogType.INFO,
            name="event.updated",
            content=f"Event {saved.code} updated (name={saved.name}, date={saved.date})",
            event_id=saved.id,
            audit=audit,
        )
        return saved