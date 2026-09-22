"""Logging helper for use cases.

Persists structured entries through the LogRepository port AND forwards a
standard Python log record (info/warning/error) to the configured handlers.
"""

import logging
from uuid import UUID, uuid4

from domain.entities.log_entry import AuditContext, LogEntry, LogType
from domain.repositories.log_repository import LogRepository
from domain.utils import utcnow

logger = logging.getLogger("application")

_LOG_LEVELS = {
    LogType.INFO: logging.INFO,
    LogType.WARNING: logging.WARNING,
    LogType.ERROR: logging.ERROR,
}


def record_log(
    log_repository: LogRepository | None,
    *,
    log_type: LogType,
    name: str,
    content: str,
    user_id: UUID | None = None,
    event_id: UUID | None = None,
    audit: AuditContext | None = None,
    stack_trace: str | None = None,
) -> None:
    """Emit a log entry (DB persistence + Python logging)."""
    entry = LogEntry(
        id=uuid4(),
        created_at=utcnow(),
        type=log_type,
        name=name,
        content=content,
        ip_address=audit.ip_address if audit else None,
        user_agent=audit.user_agent if audit else None,
        endpoint=audit.endpoint if audit else None,
        http_method=audit.http_method if audit else None,
        stack_trace=stack_trace,
        user_id=user_id,
        event_id=event_id,
    )
    entry.validate()

    level = _LOG_LEVELS.get(log_type, logging.INFO)
    logger.log(level, "%s user_id=%s event_id=%s :: %s", name, user_id, event_id, content)

    if log_repository is not None:
        try:
            log_repository.create(entry)
        except Exception:  # pragma: no cover - logging must never break business logic
            logger.exception("failed to persist log entry %s", name)