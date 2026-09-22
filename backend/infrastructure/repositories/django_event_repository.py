"""Django implementation of the EventRepository port."""

from uuid import UUID

from domain.entities.event import Event
from domain.repositories.event_repository import EventRepository

from infrastructure.orm.models import EventORM
from infrastructure.repositories.mappers import (
    event_domain_to_orm,
    event_orm_to_domain,
)
from domain.utils import utcnow


class DjangoEventRepository(EventRepository):
    def create(self, event: Event) -> Event:
        row = EventORM.objects.create(**event_domain_to_orm(event))
        return event_orm_to_domain(row)

    def get_by_id(self, event_id: UUID) -> Event | None:
        row = EventORM.objects.filter(pk=event_id, deleted_at__isnull=True).first()
        return event_orm_to_domain(row) if row else None

    def code_exists(self, code: str) -> bool:
        return EventORM.objects.filter(code=code, deleted_at__isnull=True).exists()

    def list(self, *, code: str | None = None) -> list[Event]:
        qs = EventORM.objects.filter(deleted_at__isnull=True)
        if code:
            qs = qs.filter(code=code)
        return [event_orm_to_domain(row) for row in qs.order_by("date")]

    def save(self, event: Event) -> Event:
        EventORM.objects.filter(pk=event.id).update(**event_domain_to_orm(event))
        row = EventORM.objects.get(pk=event.id)
        return event_orm_to_domain(row)

    def soft_delete(self, event_id: UUID) -> None:
        EventORM.objects.filter(pk=event_id).update(
            deleted_at=utcnow(), updated_at=utcnow()
        )