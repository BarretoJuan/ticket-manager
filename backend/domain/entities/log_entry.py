"""Log entry entity: audit/log records persisted to the LOGS table."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from domain.exceptions import LogValidationError


class LogType(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class AuditContext:
    """Request metadata attached to a log entry (optional, defaults to None)."""

    ip_address: str | None = None
    user_agent: str | None = None
    endpoint: str | None = None
    http_method: str | None = None


@dataclass(frozen=True)
class LogEntry:
    id: UUID
    created_at: datetime
    type: str  # LogType.INFO | WARNING | ERROR
    name: str
    content: str
    ip_address: str | None = None
    user_agent: str | None = None
    endpoint: str | None = None
    http_method: str | None = None
    status_code: str | None = None
    stack_trace: str | None = None
    user_id: UUID | None = None
    event_id: UUID | None = None

    def validate(self) -> None:
        if self.type not in (LogType.INFO, LogType.WARNING, LogType.ERROR):
            raise LogValidationError(f"invalid log type {self.type!r}")
        if not self.name:
            raise LogValidationError("log name cannot be empty")
        if not self.content:
            raise LogValidationError("log content cannot be empty")