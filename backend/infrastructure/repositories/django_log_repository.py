"""Django implementation of the LogRepository port."""

from domain.entities.log_entry import LogEntry
from domain.repositories.log_repository import LogRepository

from infrastructure.orm.models import LogORM
from infrastructure.repositories.mappers import log_orm_to_domain


class DjangoLogRepository(LogRepository):
    def create(self, entry: LogEntry) -> LogEntry:
        row = LogORM.objects.create(
            type=entry.type,
            name=entry.name,
            content=entry.content,
            ip_address=entry.ip_address,
            user_agent=entry.user_agent,
            endpoint=entry.endpoint,
            http_method=entry.http_method,
            status_code=entry.status_code,
            stack_trace=entry.stack_trace,
            user_id=entry.user_id,
            event_id=entry.event_id,
        )
        row.refresh_from_db()
        return log_orm_to_domain(row)
