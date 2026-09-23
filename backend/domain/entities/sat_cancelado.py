"""SAT cancelled tax-payers entity (art. 69 CFF "Cancelados" open data)."""

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from domain.exceptions import SatValidationError


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


@dataclass(frozen=True)
class SatCancelado:
    """A single row of the SAT "Cancelados" file.

    The same ``rfc`` can legitimately appear in several *distinct* rows (a
    tax-payer may be cancelled more than once, at different dates/amounts), so
    ``rfc`` is not unique: rows are instead de-duplicated by their full
    content hash (see :func:`sat_cancelado_row_hash`).
    """

    rfc: str
    razon_social: str
    tipo_persona: str
    supuesto: str
    fecha_de_cancelacion: date
    monto: Decimal
    fecha_de_publicacion: date
    entidad_federativa: str

    def validate(self) -> None:
        if not self.rfc:
            raise SatValidationError("rfc cannot be empty")
        if self.fecha_de_cancelacion is None:
            raise SatValidationError("fecha_de_cancelacion is required")
        if self.fecha_de_publicacion is None:
            raise SatValidationError("fecha_de_publicacion is required")
        if self.monto is None or self.monto < 0:
            raise SatValidationError("monto must be zero or greater")


def sat_cancelado_row_hash(record: SatCancelado) -> str:
    """sha256 of the canonicalized row content.

    Rows that only differ in insignificant formatting (extra whitespace in the
    free-text columns, amount decimal padding) hash the same, so an already
    imported row is skipped instead of being stored again. The canonical form
    is mirrored by the ``0004`` data migration so backfilled rows dedupe
    correctly against freshly imported ones — keep both in sync.
    """
    digest = hashlib.sha256()
    parts = (
        record.rfc.strip().upper(),
        _collapse_whitespace(record.razon_social),
        record.tipo_persona.strip(),
        _collapse_whitespace(record.supuesto),
        record.fecha_de_cancelacion.isoformat(),
        f"{record.monto:.2f}",
        record.fecha_de_publicacion.isoformat(),
        record.entidad_federativa.strip(),
    )
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()
