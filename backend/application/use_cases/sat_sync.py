"""SAT "Cancelados" sync use case (art. 69 CFF open data).

``start`` performs the cheap, synchronous pre-checks — the time-based cooldown
and the single-slot concurrent-run guard — and records a ``processing`` history
row. ``run`` performs the heavy, synchronous work (download, hash, stream-import)
and is designed to be executed on a background thread by
:class:`SatSyncRunner`. It never raises: every failure is recorded as an
``error`` history row.

The CSV (≈185k rows / ≈20 MB at the time of writing) is never loaded into
memory: the download streams to a temp file while a sha256 is computed, and the
file is parsed row by row with ``csv.reader`` and imported in batches. Import
de-duplicates by full row content hash: identical rows already stored (from
this file or a previous publication) are skipped — the same RFC can also appear
in several distinct rows, which are all kept.
"""

import csv
import logging
import re
import shutil
import tempfile
import time
import traceback
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from application.logging_utils import record_log
from domain.entities.log_entry import AuditContext, LogType
from domain.entities.sat_cancelado import (
    SatCancelado,
    sat_cancelado_row_hash,
)
from domain.entities.sat_history import SatHistory
from domain.exceptions import (
    SatHistoryNotFoundError,
    SatParseError,
    SatValidationError,
)
from domain.repositories.log_repository import LogRepository
from domain.repositories.sat_repository import SatRepository
from domain.services.sat_data_service import SatDataService
from domain.utils import utcnow

logger = logging.getLogger("application")

# The file is small per-row; cap individual fields so a pathological row can
# never inflate memory or the database columns beyond reason.
_MAX_FIELD_LENGTH = 10_000

#: CSV column aliases (ASCII-normalized). The real SAT header is:
#: RFC, RAZON SOCIAL, TIPO PERSONA, SUPUESTO, FECHA DE CANCELACION,
#: MONTO, FECHA DE PUBLICACION, ENTIDAD FEDERATIVA
_HEADER_ALIASES = {
    "rfc": ("rfc",),
    "razon_social": ("razon social", "nombre, denominacion o razon social"),
    "tipo_persona": ("tipo persona", "tipo de persona"),
    "supuesto": ("supuesto",),
    "fecha_de_cancelacion": ("fecha de cancelacion",),
    "monto": ("monto", "monto total de las operaciones"),
    "fecha_de_publicacion": ("fecha de publicacion",),
    "entidad_federativa": ("entidad federativa",),
}


@dataclass(frozen=True)
class SatSyncResult:
    """Outcome of the synchronous ``start`` pre-checks."""

    status: str  # "started" | "in_progress" | "cooldown_skip"
    history: SatHistory | None = None
    reason: str | None = None
    last_sync: SatHistory | None = None
    next_allowed_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Pure parsing helpers (unit-testable)
# --------------------------------------------------------------------------- #
def normalize_header(value: str) -> str:
    """Lowercase, strip accents/case and collapse whitespace in a CSV header."""
    value = value.strip().lower()
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"\s+", " ", value)


def index_columns(headers: list[str]) -> dict[str, int]:
    """Map canonical field names to their column index by header alias."""
    normalized = [normalize_header(h) for h in headers]
    columns: dict[str, int] = {}
    for field, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                columns[field] = normalized.index(alias)
                break
    return columns


def parse_sat_date(value: str) -> date | None:
    """Parse the CSV ``dd/mm/yyyy`` format; return None when invalid."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_sat_amount(value: str) -> Decimal | None:
    """Parse a SAT monetary value (``1,390,273`` / ``0`` / ``1,234.56``)."""
    cleaned = value.replace(",", "").replace("$", "").replace(" ", "").strip()
    if not cleaned:
        return Decimal("0")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    # ``NaN``/``Infinity`` would poison the comparison below (NaN comparisons
    # raise); treat any non-finite value as invalid rather than an error.
    if not amount.is_finite() or amount < 0:
        return None
    return amount


def parse_cancelado_row(raw: list[str], columns: dict[str, int]) -> SatCancelado | None:
    """Turn one CSV row into a ``SatCancelado``; None means invalid/omitted."""

    def cell(field: str) -> str:
        idx = columns.get(field)
        if idx is None or idx >= len(raw):
            return ""
        return raw[idx].strip()

    if any(
        0 <= idx < len(raw) and len(raw[idx]) > _MAX_FIELD_LENGTH
        for idx in columns.values()
    ):
        return None

    rfc = cell("rfc").upper()
    if not rfc:
        return None

    fecha_cancelacion = parse_sat_date(cell("fecha_de_cancelacion"))
    fecha_publicacion = parse_sat_date(cell("fecha_de_publicacion"))
    monto = parse_sat_amount(cell("monto"))
    if fecha_cancelacion is None or fecha_publicacion is None or monto is None:
        return None

    record = SatCancelado(
        rfc=rfc,
        razon_social=cell("razon_social"),
        tipo_persona=cell("tipo_persona"),
        supuesto=cell("supuesto"),
        fecha_de_cancelacion=fecha_cancelacion,
        monto=monto,
        fecha_de_publicacion=fecha_publicacion,
        entidad_federativa=cell("entidad_federativa"),
    )
    try:
        record.validate()
    except SatValidationError:
        return None
    return record


@contextmanager
def _open_csv_reader(file_path: Path):
    """Stream ``csv.reader`` over the file (BOM-safe, with a latin-1 fallback).

    The encoding is sniffed on the file prefix; if a later byte is not valid
    UTF-8 the ``UnicodeDecodeError`` surfaces to the caller (which records the
    run as ``error``) rather than crashing the process.
    """
    with open(file_path, "rb") as probe:
        prefix = probe.read(4096)
    try:
        prefix.decode("utf-8")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        encoding = "latin-1"
    handle = open(file_path, newline="", encoding=encoding)
    try:
        yield csv.reader(handle)
    finally:
        handle.close()


# --------------------------------------------------------------------------- #
# Use case
# --------------------------------------------------------------------------- #
class SatSync:
    def __init__(
        self,
        repository: SatRepository,
        data_service: SatDataService,
        log_repository: LogRepository | None = None,
        cooldown_minutes: int = 30,
        batch_size: int = 5000,
    ) -> None:
        self.repository = repository
        self.data_service = data_service
        self.log_repository = log_repository
        self.cooldown_minutes = cooldown_minutes
        self.batch_size = batch_size

    # -- synchronous pre-checks (HTTP request time) ---------------------- #
    def start(
        self,
        *,
        force: bool,
        user_id: UUID | None,
        audit: AuditContext | None = None,
    ) -> SatSyncResult:
        last = self.repository.latest_completed_history()
        cooldown = timedelta(minutes=self.cooldown_minutes)
        if (
            not force
            and last is not None
            and last.completed_at is not None
            and (utcnow() - last.completed_at) < cooldown
        ):
            record_log(
                self.log_repository,
                log_type=LogType.INFO,
                name="sat.sync.skipped",
                content=(
                    f"SAT sync skipped: within cooldown "
                    f"({self.cooldown_minutes} minutes)"
                ),
                user_id=user_id,
                audit=audit,
            )
            return SatSyncResult(
                status="cooldown_skip",
                reason="cooldown",
                last_sync=last,
                next_allowed_at=last.completed_at + cooldown,
            )

        history = self.repository.create_processing_history(
            user_id=user_id, started_at=utcnow()
        )
        if history is None:
            current = self.repository.get_processing_history()
            return SatSyncResult(
                status="in_progress",
                history=current,
                reason="another sync is already running",
            )

        record_log(
            self.log_repository,
            log_type=LogType.INFO,
            name="sat.sync.started",
            content=f"SAT sync started (user {user_id})",
            user_id=user_id,
            audit=audit,
        )
        return SatSyncResult(status="started", history=history)

    # -- heavy work (background thread) ---------------------------------- #
    def run(
        self,
        *,
        history_id: UUID,
        user_id: UUID | None = None,
        audit: AuditContext | None = None,
    ) -> SatHistory:
        """Download, hash and import the file; always ends in a terminal state."""
        started = time.monotonic()
        temp_dir: Path | None = None
        file_hash: str | None = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="sat_sync_"))
            download = self.data_service.download(temp_dir)
            file_hash = download.file_hash

            if self.repository.history_exists_with_hash(file_hash):
                record_log(
                    self.log_repository,
                    log_type=LogType.INFO,
                    name="sat.sync.duplicate",
                    content="SAT file already processed (identical hash); skipped",
                    user_id=user_id,
                    audit=audit,
                )
                return self.repository.complete_history(
                    history_id,
                    completed_at=utcnow(),
                    processing_time=time.monotonic() - started,
                    record_number=0,
                    omitted_number=0,
                    file_hash=file_hash,
                )

            imported, omitted = self._import_file(download.file_path)
            elapsed = time.monotonic() - started
            record_log(
                self.log_repository,
                log_type=LogType.INFO,
                name="sat.sync.completed",
                content=(
                    f"SAT sync completed: {imported} imported, {omitted} omitted "
                    f"(invalid or already stored) in {elapsed:.1f}s"
                ),
                user_id=user_id,
                audit=audit,
            )
            return self.repository.complete_history(
                history_id,
                completed_at=utcnow(),
                processing_time=elapsed,
                record_number=imported,
                omitted_number=omitted,
                file_hash=file_hash,
            )
        except Exception as exc:  # noqa: BLE001 - any failure -> error state
            elapsed = time.monotonic() - started
            logger.exception("SAT sync %s failed", history_id)
            record_log(
                self.log_repository,
                log_type=LogType.ERROR,
                name="sat.sync.failed",
                content=f"SAT sync failed: {exc}",
                user_id=user_id,
                audit=audit,
                stack_trace=traceback.format_exc(),
            )
            return self.repository.fail_history(
                history_id,
                completed_at=utcnow(),
                processing_time=elapsed,
                file_hash=file_hash,
            )
        finally:
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def get_history(self, history_id: UUID) -> SatHistory:
        history = self.repository.get_history(history_id)
        if history is None:
            raise SatHistoryNotFoundError("sat sync history not found")
        return history

    # -- internals ------------------------------------------------------- #
    def _import_file(self, file_path: Path) -> tuple[int, int]:
        """Stream the CSV and import it. Returns (imported, omitted).

        ``imported`` is the number of rows stored; ``omitted`` is the number of
        invalid rows plus rows already stored with an identical content hash.
        """
        imported = 0
        omitted = 0
        batch: dict[str, SatCancelado] = {}
        with _open_csv_reader(file_path) as reader:
            try:
                headers = next(reader)
            except StopIteration:
                raise SatParseError("empty CSV file")
            columns = index_columns(headers)
            if "rfc" not in columns:
                raise SatParseError(
                    "unrecognized CSV: no RFC column " f"(headers: {headers!r})"
                )

            for raw in reader:
                if not raw:
                    continue
                record = parse_cancelado_row(raw, columns)
                if record is None:
                    omitted += 1
                    continue
                row_hash = sat_cancelado_row_hash(record)
                if row_hash in batch:
                    # exact duplicate already queued in this batch
                    omitted += 1
                    continue
                batch[row_hash] = record
                if len(batch) >= self.batch_size:
                    result = self.repository.import_cancelados(list(batch.values()))
                    imported += result.inserted
                    omitted += result.skipped_identical
                    batch.clear()

        if batch:
            result = self.repository.import_cancelados(list(batch.values()))
            imported += result.inserted
            omitted += result.skipped_identical
        return imported, omitted
