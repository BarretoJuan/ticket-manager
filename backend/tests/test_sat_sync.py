"""SAT sync use case tests with fakes — no database required.

Verifies cooldown, concurrency guard, streaming import with content-hash
dedupe, date & amount parsing, duplicate-hash short-circuit and error handling.
"""

import csv
import hashlib
import io
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock
from uuid import uuid4

from application.services.sat_sync_runner import SatSyncRunner
from application.use_cases.sat_sync import SatSync, parse_sat_amount, parse_sat_date
from domain.entities.sat_cancelado import SatCancelado, sat_cancelado_row_hash
from domain.entities.sat_history import SatHistory, SatSyncStatus
from domain.exceptions import (
    SatDownloadError,
    SatHistoryNotFoundError,
)
from domain.repositories.log_repository import LogRepository
from domain.repositories.sat_repository import (
    SatHistoryPage,
    SatHistoryQuery,
    SatRepository,
    SatUpsertResult,
)
from domain.services.sat_data_service import SatDataService, SatDownloadResult
from domain.utils import utcnow

DEFAULT_HEADER = [
    "RFC",
    "RAZON SOCIAL",
    "TIPO PERSONA",
    "SUPUESTO",
    "FECHA DE CANCELACION",
    "MONTO",
    "FECHA DE PUBLICACION",
    "ENTIDAD FEDERATIVA",
]


def make_csv(rows, header=None) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header or DEFAULT_HEADER)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeSatDataService(SatDataService):
    def __init__(self, csv_bytes: bytes, raise_download=None):
        self.csv_bytes = csv_bytes
        self.raise_download = raise_download

    def download(self, dest_dir: Path) -> SatDownloadResult:
        if self.raise_download is not None:
            raise self.raise_download
        file_path = dest_dir / "cancelados.csv"
        file_path.write_bytes(self.csv_bytes)
        return SatDownloadResult(
            file_path=file_path, file_hash=hashlib.sha256(self.csv_bytes).hexdigest()
        )


class FakeSatRepository(SatRepository):
    def __init__(self):
        self.history: dict = {}
        self.cancelados: dict = {}
        self._processing_guard = True

    def create_processing_history(self, *, user_id, started_at):
        if not self._processing_guard:
            return None
        if any(h.status == SatSyncStatus.PROCESSING for h in self.history.values()):
            return None
        history = SatHistory(
            id=uuid4(),
            started_at=started_at,
            completed_at=None,
            user_id=user_id,
            status=SatSyncStatus.PROCESSING,
            file_hash=None,
            processing_time=None,
            record_number=0,
            omitted_number=0,
        )
        self.history[history.id] = history
        return history

    def get_processing_history(self):
        for h in self.history.values():
            if h.status == SatSyncStatus.PROCESSING:
                return h
        return None

    def latest_completed_history(self):
        completed = [
            h for h in self.history.values() if h.status == SatSyncStatus.COMPLETED
        ]
        if not completed:
            return None
        return max(completed, key=lambda h: h.completed_at)

    def history_exists_with_hash(self, file_hash):
        return any(
            h.file_hash == file_hash and h.status == SatSyncStatus.COMPLETED
            for h in self.history.values()
        )

    def complete_history(
        self,
        history_id,
        *,
        completed_at,
        processing_time,
        record_number,
        omitted_number,
        file_hash,
    ):
        h = self.history[history_id]
        updated = SatHistory(
            id=h.id,
            started_at=h.started_at,
            completed_at=completed_at,
            user_id=h.user_id,
            status=SatSyncStatus.COMPLETED,
            file_hash=file_hash,
            processing_time=processing_time,
            record_number=record_number,
            omitted_number=omitted_number,
        )
        self.history[history_id] = updated
        return updated

    def fail_history(self, history_id, *, completed_at, processing_time, file_hash):
        h = self.history[history_id]
        updated = SatHistory(
            id=h.id,
            started_at=h.started_at,
            completed_at=completed_at,
            user_id=h.user_id,
            status=SatSyncStatus.ERROR,
            file_hash=file_hash or h.file_hash,
            processing_time=processing_time,
            record_number=h.record_number,
            omitted_number=h.omitted_number,
        )
        self.history[history_id] = updated
        return updated

    def get_history(self, history_id):
        return self.history.get(history_id)

    def import_cancelados(self, records):
        inserted = 0
        skipped = 0
        for record in records:
            h = sat_cancelado_row_hash(record)
            if h in self.cancelados:
                skipped += 1
            else:
                self.cancelados[h] = record
                inserted += 1
        return SatUpsertResult(inserted=inserted, skipped_identical=skipped)

    def by_rfc(self, rfc):
        return [r for r in self.cancelados.values() if r.rfc == rfc]

    def list_history(self, query: SatHistoryQuery) -> SatHistoryPage:
        items = sorted(self.history.values(), key=lambda h: h.started_at, reverse=True)[
            query.offset : query.offset + query.limit
        ]
        return SatHistoryPage(items=items, total=len(self.history))


class FakeLogRepository(LogRepository):
    def __init__(self):
        self.entries = []

    def create(self, entry):
        self.entries.append(entry)
        return entry


def make_use_case(repo=None, service=None, cooldown_minutes=30, batch_size=10):
    return SatSync(
        repo or FakeSatRepository(),
        service or FakeSatDataService(b""),
        FakeLogRepository(),
        cooldown_minutes=cooldown_minutes,
        batch_size=batch_size,
    )


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
class SatParsingTests(unittest.TestCase):
    def test_parse_sat_date_converts_ddmmyyyy(self):
        self.assertEqual(parse_sat_date("28/05/2019"), date(2019, 5, 28))
        self.assertEqual(parse_sat_date("01/11/2015"), date(2015, 11, 1))

    def test_parse_sat_date_rejects_invalid(self):
        for value in ("", "2019-05-28", "28/05/19", "32/13/2019", None):
            self.assertIsNone(parse_sat_date(value or ""))

    def test_parse_sat_amount(self):
        self.assertEqual(parse_sat_amount("1,390,273"), Decimal("1390273"))
        self.assertEqual(parse_sat_amount("0"), Decimal("0"))
        self.assertEqual(parse_sat_amount("1,234.56"), Decimal("1234.56"))
        self.assertEqual(parse_sat_amount("$ 3,080"), Decimal("3080"))
        self.assertEqual(parse_sat_amount(""), Decimal("0"))

    def test_parse_sat_amount_rejects_invalid(self):
        self.assertIsNone(parse_sat_amount("abc"))
        self.assertIsNone(parse_sat_amount("-5"))


# --------------------------------------------------------------------------- #
# start() — cooldown / concurrency
# --------------------------------------------------------------------------- #
class SatSyncStartTests(unittest.TestCase):
    def test_start_creates_processing_history(self):
        repo = FakeSatRepository()
        result = make_use_case(repo=repo).start(force=False, user_id=uuid4())
        self.assertEqual(result.status, "started")
        self.assertEqual(result.history.status, SatSyncStatus.PROCESSING)

    def test_start_cooldown_skip(self):
        repo = FakeSatRepository()
        repo.history[uuid4()] = SatHistory(
            id=uuid4(),
            started_at=utcnow() - timedelta(days=1),
            completed_at=utcnow() - timedelta(minutes=5),
            user_id=None,
            status=SatSyncStatus.COMPLETED,
            file_hash="h",
            processing_time=1.0,
            record_number=10,
            omitted_number=0,
        )
        result = make_use_case(repo=repo).start(force=False, user_id=uuid4())
        self.assertEqual(result.status, "cooldown_skip")
        self.assertEqual(result.reason, "cooldown")
        self.assertIsNotNone(result.next_allowed_at)
        self.assertIsNone(repo.get_processing_history())

    def test_force_bypasses_cooldown(self):
        repo = FakeSatRepository()
        repo.history[uuid4()] = SatHistory(
            id=uuid4(),
            started_at=utcnow() - timedelta(days=1),
            completed_at=utcnow() - timedelta(minutes=5),
            user_id=None,
            status=SatSyncStatus.COMPLETED,
            file_hash="h",
            processing_time=1.0,
            record_number=10,
            omitted_number=0,
        )
        result = make_use_case(repo=repo).start(force=True, user_id=uuid4())
        self.assertEqual(result.status, "started")

    def test_start_blocks_second_concurrent_run(self):
        repo = FakeSatRepository()
        use_case = make_use_case(repo=repo)
        first = use_case.start(force=False, user_id=uuid4())
        second = use_case.start(force=False, user_id=uuid4())
        self.assertEqual(first.status, "started")
        self.assertEqual(second.status, "in_progress")
        self.assertEqual(second.history.id, first.history.id)

    def test_get_history_not_found(self):
        with self.assertRaises(SatHistoryNotFoundError):
            make_use_case().get_history(uuid4())


# --------------------------------------------------------------------------- #
# run() — download / import / dedupe / errors
# --------------------------------------------------------------------------- #
class SatSyncRunTests(unittest.TestCase):
    def test_run_imports_all_distinct_rows_sharing_an_rfc(self):
        csv_bytes = make_csv(
            [
                [
                    "AAA010101AAA",
                    "EMPRESA UNO SA DE CV",
                    "M",
                    "CANCELADOS",
                    "28/05/2019",
                    "1,390,273",
                    "20/08/2019",
                    "BAJA CALIFORNIA SUR",
                ],
                [
                    "BBB020202BBB",
                    "EMPRESA DOS SA DE CV",
                    "M",
                    "CANCELADOS",
                    "13/02/2014",
                    "0",
                    "01/11/2015",
                    "MEXICO",
                ],
                # same RFC but a distinct row -> kept (not merged)
                [
                    "AAA010101AAA",
                    "EMPRESA UNO RENOMBRADA",
                    "M",
                    "CANCELADOS",
                    "10/10/2020",
                    "100",
                    "11/11/2020",
                    "NUEVO LEON",
                ],
            ]
        )
        repo = FakeSatRepository()
        use_case = make_use_case(repo=repo, service=FakeSatDataService(csv_bytes))
        result = use_case.start(force=False, user_id=uuid4())
        history = use_case.run(history_id=result.history.id, user_id=uuid4())

        self.assertEqual(history.status, SatSyncStatus.COMPLETED)
        self.assertEqual(history.record_number, 3)
        self.assertEqual(history.omitted_number, 0)
        self.assertEqual(len(repo.cancelados), 3)
        same_rfc = repo.by_rfc("AAA010101AAA")
        self.assertEqual(len(same_rfc), 2)
        # both distinct rows preserved for the same RFC
        self.assertEqual(
            {r.fecha_de_cancelacion for r in same_rfc},
            {date(2019, 5, 28), date(2020, 10, 10)},
        )

    def test_run_skips_exact_duplicate_rows(self):
        csv_bytes = make_csv(
            [
                [
                    "AOAC580716NP7",
                    "CARMEN MARIA  ACOSTA  AZUETA",
                    "F",
                    "CANCELADOS POR INCOSTEABILIDAD",
                    "17/04/2020",
                    "980",
                    "08/07/2020",
                    "QUINTANA ROO",
                ],
                # byte-for-byte identical row -> collapsed within the batch
                [
                    "AOAC580716NP7",
                    "CARMEN MARIA  ACOSTA  AZUETA",
                    "F",
                    "CANCELADOS POR INCOSTEABILIDAD",
                    "17/04/2020",
                    "980",
                    "08/07/2020",
                    "QUINTANA ROO",
                ],
            ]
        )
        repo = FakeSatRepository()
        use_case = make_use_case(repo=repo, service=FakeSatDataService(csv_bytes))
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.COMPLETED)
        self.assertEqual(history.record_number, 1)
        self.assertEqual(history.omitted_number, 1)
        self.assertEqual(len(repo.cancelados), 1)

    def test_run_skips_rows_already_stored_across_batches(self):
        csv_bytes = make_csv(
            [
                [
                    "AAA010101AAA",
                    "EMPRESA UNO SA DE CV",
                    "M",
                    "CANCELADOS",
                    "28/05/2019",
                    "1,000",
                    "20/08/2019",
                    "MEXICO",
                ],
                # identical copy arriving in a separate batch -> DB-level skip
                [
                    "AAA010101AAA",
                    "EMPRESA UNO SA DE CV",
                    "M",
                    "CANCELADOS",
                    "28/05/2019",
                    "1,000",
                    "20/08/2019",
                    "MEXICO",
                ],
                [
                    "BBB020202BBB",
                    "EMPRESA DOS SA DE CV",
                    "M",
                    "CANCELADOS",
                    "13/02/2014",
                    "0",
                    "01/11/2015",
                    "MEXICO",
                ],
            ]
        )
        repo = FakeSatRepository()
        use_case = make_use_case(
            repo=repo, service=FakeSatDataService(csv_bytes), batch_size=1
        )
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.COMPLETED)
        self.assertEqual(history.record_number, 2)
        self.assertEqual(history.omitted_number, 1)
        self.assertEqual(len(repo.cancelados), 2)

    def test_run_converts_dates_and_amounts(self):
        csv_bytes = make_csv(
            [
                [
                    "CCC030303CCC",
                    "MONTOS SA",
                    "M",
                    "CANCELADOS POR INSOLVENCIA",
                    "30/09/2019",
                    "482,088",
                    "18/08/2021",
                    "MORELOS",
                ]
            ]
        )
        repo = FakeSatRepository()
        use_case = make_use_case(repo=repo, service=FakeSatDataService(csv_bytes))
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        record = repo.by_rfc("CCC030303CCC")[0]
        self.assertEqual(history.record_number, 1)
        self.assertEqual(record.fecha_de_cancelacion, date(2019, 9, 30))
        self.assertEqual(record.fecha_de_publicacion, date(2021, 8, 18))
        self.assertEqual(record.monto, Decimal("482088"))

    def test_run_counts_omitted_rows(self):
        csv_bytes = make_csv(
            [
                # empty RFC
                [
                    "",
                    "SIN RFC SA",
                    "M",
                    "CANCELADOS",
                    "01/01/2020",
                    "0",
                    "01/02/2020",
                    "MEXICO",
                ],
                # invalid date
                [
                    "DDD040404DDD",
                    "FECHA MALA SA",
                    "M",
                    "CANCELADOS",
                    "not-adate",
                    "0",
                    "01/02/2020",
                    "MEXICO",
                ],
                # invalid amount
                [
                    "EEE050505EEE",
                    "MONTO MALO SA",
                    "M",
                    "CANCELADOS",
                    "01/01/2020",
                    "NaN",
                    "01/02/2020",
                    "MEXICO",
                ],
                # valid row
                [
                    "FFF060606FFF",
                    "BUENA SA",
                    "F",
                    "CANCELADOS",
                    "01/01/2020",
                    "10",
                    "01/02/2020",
                    "JALISCO",
                ],
            ]
        )
        repo = FakeSatRepository()
        use_case = make_use_case(repo=repo, service=FakeSatDataService(csv_bytes))
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.COMPLETED)
        self.assertEqual(history.record_number, 1)
        self.assertEqual(history.omitted_number, 3)
        self.assertEqual(len(repo.cancelados), 1)

    def test_run_short_circuits_on_duplicate_hash(self):
        csv_bytes = make_csv(
            [
                [
                    "AAA010101AAA",
                    "EMPRESA",
                    "M",
                    "CANCELADOS",
                    "01/01/2020",
                    "0",
                    "01/02/2020",
                    "MEXICO",
                ]
            ]
        )
        repo = FakeSatRepository()
        repo.history[uuid4()] = SatHistory(
            id=uuid4(),
            started_at=utcnow() - timedelta(days=1),
            completed_at=utcnow() - timedelta(days=1),
            user_id=None,
            status=SatSyncStatus.COMPLETED,
            file_hash=hashlib.sha256(csv_bytes).hexdigest(),
            processing_time=2.0,
            record_number=100,
            omitted_number=0,
        )
        use_case = make_use_case(repo=repo, service=FakeSatDataService(csv_bytes))
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.COMPLETED)
        self.assertEqual(history.record_number, 0)
        self.assertEqual(repo.cancelados, {})

    def test_run_marks_error_on_download_failure(self):
        use_case = make_use_case(
            service=FakeSatDataService(
                b"", raise_download=SatDownloadError("SAT is down")
            )
        )
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.ERROR)
        self.assertIsNotNone(history.completed_at)
        self.assertIsNotNone(history.processing_time)

    def test_run_marks_error_on_unrecognized_csv(self):
        csv_bytes = make_csv(
            [["x", "y", "z"]],
            header=["NO", "SOMETHING", "ELSE"],
        )
        use_case = make_use_case(service=FakeSatDataService(csv_bytes))
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.ERROR)

    def test_run_marks_error_on_missing_rfc_column(self):
        csv_bytes = make_csv(
            [["z"]],
            header=["SOLO UNA COLUMNA"],
        )
        use_case = make_use_case(service=FakeSatDataService(csv_bytes))
        history = use_case.run(
            history_id=use_case.start(force=False, user_id=uuid4()).history.id
        )
        self.assertEqual(history.status, SatSyncStatus.ERROR)


# --------------------------------------------------------------------------- #
# Row content hash
# --------------------------------------------------------------------------- #
class SatRowHashTests(unittest.TestCase):
    def _record(self, **overrides):
        base = dict(
            rfc="AAA010101AAA",
            razon_social="EMPRESA UNO SA DE CV",
            tipo_persona="M",
            supuesto="CANCELADOS",
            fecha_de_cancelacion=date(2019, 5, 28),
            monto=Decimal("1000"),
            fecha_de_publicacion=date(2020, 8, 20),
            entidad_federativa="MEXICO",
        )
        base.update(overrides)
        return SatCancelado(**base)

    def test_identical_rows_hash_the_same(self):
        self.assertEqual(
            sat_cancelado_row_hash(self._record()),
            sat_cancelado_row_hash(self._record()),
        )

    def test_insignificant_whitespace_does_not_change_hash(self):
        compact = self._record(razon_social="EMPRESA UNO SA DE CV")
        padded = self._record(razon_social="  EMPRESA  UNO   SA DE CV  ")
        self.assertEqual(
            sat_cancelado_row_hash(compact), sat_cancelado_row_hash(padded)
        )

    def test_content_differences_change_hash(self):
        base = self._record()
        variants = [
            self._record(rfc="BBB020202BBB"),
            self._record(monto=Decimal("1001")),
            self._record(fecha_de_cancelacion=date(2020, 5, 28)),
            self._record(fecha_de_publicacion=date(2020, 9, 20)),
            self._record(supuesto="CANCELADOS POR INSOLVENCIA"),
            self._record(entidad_federativa="NUEVO LEON"),
            self._record(tipo_persona="F"),
            self._record(razon_social="OTRA EMPRESA SA"),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(
                    sat_cancelado_row_hash(base), sat_cancelado_row_hash(variant)
                )

    def test_amount_is_canonicalized_to_two_decimals(self):
        self.assertEqual(
            sat_cancelado_row_hash(self._record(monto=Decimal("1000.00"))),
            sat_cancelado_row_hash(self._record(monto=Decimal("1000"))),
        )

    def test_rfc_is_canonicalized_to_uppercase(self):
        self.assertEqual(
            sat_cancelado_row_hash(self._record(rfc="aaa010101aaa")),
            sat_cancelado_row_hash(self._record(rfc="AAA010101AAA")),
        )


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
class SatSyncRunnerTests(unittest.TestCase):
    def test_runner_enqueues_started_work(self):
        use_case = make_use_case()
        runner = SatSyncRunner(use_case)
        with mock.patch.object(runner, "_enqueue") as enqueue:
            result = runner.start(force=False, user_id=uuid4())
        self.assertEqual(result.status, "started")
        self.assertEqual(enqueue.call_count, 1)

    def test_runner_does_not_enqueue_skipped_work(self):
        repo = FakeSatRepository()
        repo.history[uuid4()] = SatHistory(
            id=uuid4(),
            started_at=utcnow() - timedelta(days=1),
            completed_at=utcnow() - timedelta(minutes=5),
            user_id=None,
            status=SatSyncStatus.COMPLETED,
            file_hash="h",
            processing_time=1.0,
            record_number=10,
            omitted_number=0,
        )
        runner = SatSyncRunner(make_use_case(repo=repo))
        with mock.patch.object(runner, "_enqueue") as enqueue:
            result = runner.start(force=False, user_id=uuid4())
        self.assertEqual(result.status, "cooldown_skip")
        enqueue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
