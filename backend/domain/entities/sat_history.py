"""SAT sync history entity — one row per sync run."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from domain.exceptions import SatValidationError


class SatSyncStatus(StrEnum):
    """Lifecycle of a sync run."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(frozen=True)
class SatHistory:
    """A single SAT sync run.

    Used for the cooldown window (``latest_completed``), the single-slot
    processing guard and as an audit record of every downloaded file.
    """

    id: UUID
    started_at: datetime
    completed_at: datetime | None
    user_id: UUID | None
    status: str  # SatSyncStatus
    file_hash: str | None
    processing_time: float | None
    record_number: int
    omitted_number: int

    def validate(self) -> None:
        if self.status not in (
            SatSyncStatus.PROCESSING,
            SatSyncStatus.COMPLETED,
            SatSyncStatus.ERROR,
        ):
            raise SatValidationError(f"invalid sat sync status {self.status!r}")
        if self.record_number < 0 or self.omitted_number < 0:
            raise SatValidationError("record counts cannot be negative")
