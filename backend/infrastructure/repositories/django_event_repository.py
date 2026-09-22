"""Django implementation of the EventRepository port."""

from uuid import UUID

from domain.entities.event import Event
from domain.repositories.event_repository import EventPage, EventQuery, EventRepository

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

    def list(self, query: EventQuery) -> EventPage:
        base = EventORM.objects.filter(deleted_at__isnull=True)
        qs = self._apply_filters(base, query)
        total = qs.count()
        rows = qs.order_by("date")[query.offset : query.offset + query.limit]
        return EventPage(
            items=[event_orm_to_domain(row) for row in rows],
            total=total,
        )

    def _apply_filters(self, qs, query: EventQuery):
        if query.code:
            qs = qs.filter(code=query.code)
        if query.name:
            qs = qs.filter(name__icontains=query.name)
        if query.date_from is not None:
            qs = qs.filter(date__gte=query.date_from)
        if query.date_to is not None:
            qs = qs.filter(date__lte=query.date_to)
        if query.availability == "available":
            qs = qs.filter(available_tickets__gt=0)
        elif query.availability == "sold_out":
            qs = qs.filter(available_tickets=0)
        return qs

    def save(self, event: Event) -> Event:
        EventORM.objects.filter(pk=event.id).update(**event_domain_to_orm(event))
        row = EventORM.objects.get(pk=event.id)
        return event_orm_to_domain(row)

    def soft_delete(self, event_id: UUID) -> None:
        EventORM.objects.filter(pk=event_id).update(
            deleted_at=utcnow(), updated_at=utcnow()
        )
