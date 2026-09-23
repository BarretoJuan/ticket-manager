"""Django/PostgreSQL implementation of the SatRepository port.

The single-slot concurrent-run guard uses a PostgreSQL advisory xact lock so it
is safe across threads and processes (e.g. multiple WSGI workers): only one
``processing`` history row can exist at a time.

Row import is de-duplicated by content hash: per batch we look up already
stored ``row_hash`` values, then plain-insert only the new rows. There is no
``ON CONFLICT … UPDATE`` anymore — ``rfc`` is deliberately not unique (the same
RFC can appear in several distinct rows), and re-published identical rows are
simply skipped.
"""

from datetime import datetime
from uuid import UUID

from django.db import connection, transaction

from domain.entities.sat_cancelado import SatCancelado, sat_cancelado_row_hash
from domain.entities.sat_history import SatHistory, SatSyncStatus
from domain.repositories.sat_repository import (
    SatHistoryPage,
    SatHistoryQuery,
    SatRepository,
    SatUpsertResult,
)

from infrastructure.orm.models import SatCanceladoORM, SatHistoryORM
from infrastructure.repositories.mappers import (
    sat_cancelado_domain_to_orm,
    sat_history_orm_to_domain,
)

#: Advisory lock key ("SATS") used to serialize sync starts process-wide.
_PROCESSING_LOCK_KEY = 1397705299

_COMPLETE_HISTORY_FIELDS = [
    "status",
    "completed_at",
    "processing_time",
    "record_number",
    "omitted_number",
    "file_hash",
]


class DjangoSatRepository(SatRepository):
    def create_processing_history(
        self, *, user_id: UUID | None, started_at: datetime
    ) -> SatHistory | None:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_try_advisory_xact_lock(%s)", (_PROCESSING_LOCK_KEY,)
                )
                acquired = cursor.fetchone()[0]
            if not acquired:
                return None
            if SatHistoryORM.objects.filter(status=SatSyncStatus.PROCESSING).exists():
                return None
            row = SatHistoryORM.objects.create(
                user_id=user_id,
                started_at=started_at,
                status=SatSyncStatus.PROCESSING,
            )
            return sat_history_orm_to_domain(row)

    def get_processing_history(self) -> SatHistory | None:
        row = (
            SatHistoryORM.objects.filter(status=SatSyncStatus.PROCESSING)
            .order_by("-started_at")
            .first()
        )
        return sat_history_orm_to_domain(row) if row else None

    def latest_completed_history(self) -> SatHistory | None:
        row = (
            SatHistoryORM.objects.filter(status=SatSyncStatus.COMPLETED)
            .order_by("-completed_at")
            .first()
        )
        return sat_history_orm_to_domain(row) if row else None

    def history_exists_with_hash(self, file_hash: str) -> bool:
        return SatHistoryORM.objects.filter(
            file_hash=file_hash, status=SatSyncStatus.COMPLETED
        ).exists()

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
        row = SatHistoryORM.objects.get(pk=history_id)
        row.status = SatSyncStatus.COMPLETED
        row.completed_at = completed_at
        row.processing_time = processing_time
        row.record_number = record_number
        row.omitted_number = omitted_number
        row.file_hash = file_hash
        row.save(update_fields=_COMPLETE_HISTORY_FIELDS)
        return sat_history_orm_to_domain(row)

    def fail_history(
        self,
        history_id: UUID,
        *,
        completed_at: datetime,
        processing_time: float,
        file_hash: str | None,
    ) -> SatHistory:
        row = SatHistoryORM.objects.get(pk=history_id)
        row.status = SatSyncStatus.ERROR
        row.completed_at = completed_at
        row.processing_time = processing_time
        if file_hash:
            row.file_hash = file_hash
        row.save(update_fields=_COMPLETE_HISTORY_FIELDS)
        return sat_history_orm_to_domain(row)

    def get_history(self, history_id: UUID) -> SatHistory | None:
        row = SatHistoryORM.objects.filter(pk=history_id).first()
        return sat_history_orm_to_domain(row) if row else None

    def import_cancelados(self, records: list[SatCancelado]) -> SatUpsertResult:
        """Insert rows whose content hash is not yet stored; skip the rest."""
        if not records:
            return SatUpsertResult(inserted=0, skipped_identical=0)
        hashed = [(sat_cancelado_row_hash(record), record) for record in records]
        with transaction.atomic():
            stored = set(
                SatCanceladoORM.objects.filter(
                    row_hash__in=[h for h, _ in hashed]
                ).values_list("row_hash", flat=True)
            )
            rows = [
                SatCanceladoORM(**sat_cancelado_domain_to_orm(record))
                for h, record in hashed
                if h not in stored
            ]
            if rows:
                SatCanceladoORM.objects.bulk_create(rows)
        return SatUpsertResult(
            inserted=len(rows),
            skipped_identical=len(hashed) - len(rows),
        )

    def list_history(self, query: SatHistoryQuery) -> SatHistoryPage:
        total = SatHistoryORM.objects.count()
        rows = SatHistoryORM.objects.order_by("-started_at")[
            query.offset : query.offset + query.limit
        ]
        return SatHistoryPage(
            items=[sat_history_orm_to_domain(row) for row in rows],
            total=total,
        )
