"""SAT repository port (art. 69 CFF "Cancelados" sync)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.entities.sat_cancelado import SatCancelado
from domain.entities.sat_history import SatHistory


@dataclass(frozen=True)
class SatHistoryQuery:
    """Pagination input for listing sync history."""

    offset: int = 0
    limit: int = 20


@dataclass(frozen=True)
class SatHistoryPage:
    """A single page of sync history plus the total number of runs."""

    items: list[SatHistory]
    total: int


@dataclass(frozen=True)
class SatUpsertResult:
    """Outcome of importing one batch of "Cancelados" rows."""

    inserted: int  # rows stored (content not present before)
    skipped_identical: int  # rows already stored with the same content hash


class SatRepository(ABC):
    @abstractmethod
    def create_processing_history(
        self, *, user_id: UUID | None, started_at: datetime
    ) -> SatHistory | None:
        """Atomically reserve the single running-sync slot.

        Returns ``None`` when another sync is already in progress (the
        implementation guards against concurrent runs across threads and
        processes).
        """

    @abstractmethod
    def get_processing_history(self) -> SatHistory | None:
        """Return the currently processing history, if any."""

    @abstractmethod
    def latest_completed_history(self) -> SatHistory | None:
        """Return the most recent completed history (cooldown reference)."""

    @abstractmethod
    def history_exists_with_hash(self, file_hash: str) -> bool:
        """True when a completed history with this exact file hash exists."""

    @abstractmethod
    def complete_history(
        self,
        history_id: UUID,
        *,
        completed_at: datetime,
        processing_time: float,
        record_number: int,
        omitted_number: int,
        file_hash: str,
    ) -> SatHistory:
        """Mark a history row as completed."""

    @abstractmethod
    def fail_history(
        self,
        history_id: UUID,
        *,
        completed_at: datetime,
        processing_time: float,
        file_hash: str | None,
    ) -> SatHistory:
        """Mark a history row as errored."""

    @abstractmethod
    def get_history(self, history_id: UUID) -> SatHistory | None:
        """Return a history row by id, or None."""

    @abstractmethod
    def import_cancelados(self, records: list[SatCancelado]) -> SatUpsertResult:
        """Store rows whose full-content hash is not yet in the table.

        Rows already stored with the same content hash are skipped (counted in
        ``skipped_identical``). Each record in a call must have a distinct
        content hash (the caller batches accordingly).
        """

    @abstractmethod
    def list_history(self, query: SatHistoryQuery) -> SatHistoryPage:
        """List sync history newest-first, paginated."""
