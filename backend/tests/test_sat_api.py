"""SAT sync API tests (APIClient + PostgreSQL, SAT downloader mocked).

The runner is patched to execute synchronously so the full
download -> import -> complete flow is deterministic.
"""

from datetime import timedelta
from unittest import mock
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from application.services.sat_sync_runner import SatSyncRunner
from application.use_cases.sat_sync import SatSync
from domain.exceptions import SatDownloadError
from domain.utils import utcnow
from infrastructure.orm.models import (
    SatCanceladoORM,
    SatHistoryORM,
    UserORM,
)
from infrastructure.repositories.django_sat_repository import DjangoSatRepository
from tests.test_sat_sync import FakeSatDataService, make_csv

import presentation.views.sat_views as sat_views

PASSWORD = "Test12345!"


def _login(email, password=PASSWORD):
    resp = APIClient().post(
        "/api/v1/login", {"email": email, "password": password}, format="json"
    )
    assert resp.status_code == 200, resp.content
    return resp.data["access"]


def _make_sync_runner(csv_bytes, raise_download=None):
    """Real PG repository + fake downloader, executed synchronously."""
    repository = DjangoSatRepository()
    service = FakeSatDataService(csv_bytes, raise_download=raise_download)
    use_case = SatSync(repository, service, cooldown_minutes=30, batch_size=5000)

    def sync_enqueue(history_id, user_id, audit):
        use_case.run(history_id=history_id, user_id=user_id, audit=audit)

    runner = SatSyncRunner(use_case)
    runner._enqueue = sync_enqueue
    return runner


class SatSyncApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = UserORM.objects.create_user(
            email="sat@example.com", password=PASSWORD, role="ADMIN"
        )
        self.admin_client = APIClient()
        self.admin_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {_login('sat@example.com')}"
        )
        self.regular = UserORM.objects.create_user(
            email="user@example.com", password=PASSWORD, role="USER"
        )
        self.user_client = APIClient()
        self.user_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {_login('user@example.com')}"
        )

    # ------------------------------------------------------------------ #
    # Authorization
    # ------------------------------------------------------------------ #
    def test_sync_requires_authentication(self):
        self.assertEqual(APIClient().post("/api/v1/sat/sync").status_code, 401)
        self.assertEqual(APIClient().get("/api/v1/sat/history").status_code, 401)

    def test_sync_requires_admin(self):
        self.assertEqual(self.user_client.post("/api/v1/sat/sync").status_code, 403)
        self.assertEqual(self.user_client.get("/api/v1/sat/history").status_code, 403)

    # ------------------------------------------------------------------ #
    # Happy path: start -> status -> cooldown -> force
    # ------------------------------------------------------------------ #
    def test_sync_flow_returns_202_then_completed_status(self):
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
                ]
            ]
        )
        with mock.patch.object(
            sat_views, "get_sat_sync_runner", return_value=_make_sync_runner(csv_bytes)
        ):
            resp = self.admin_client.post("/api/v1/sat/sync")
        self.assertEqual(resp.status_code, 202, resp.content)
        self.assertEqual(resp.data["status"], "processing")
        history_id = resp.data["history_id"]

        status_resp = self.admin_client.get(f"/api/v1/sat/sync/{history_id}")
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data["status"], "completed")
        self.assertEqual(status_resp.data["record_number"], 1)
        self.assertEqual(status_resp.data["omitted_number"], 0)
        self.assertIsNotNone(status_resp.data["file_hash"])

    def test_same_rfc_distinct_rows_are_all_imported(self):
        # Regression: the old ON CONFLICT ... UPDATE crashed with
        # "ON CONFLICT DO UPDATE command cannot affect row a second time"
        # when one batch contained the same RFC twice (a legitimate, distinct
        # record). Same-RFC rows must now all be kept.
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
        with mock.patch.object(
            sat_views, "get_sat_sync_runner", return_value=_make_sync_runner(csv_bytes)
        ):
            resp = self.admin_client.post("/api/v1/sat/sync")
        self.assertEqual(resp.status_code, 202, resp.content)
        status_resp = self.admin_client.get(
            f"/api/v1/sat/sync/{resp.data['history_id']}"
        )
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data["status"], "completed")
        self.assertEqual(status_resp.data["record_number"], 2)
        self.assertEqual(status_resp.data["omitted_number"], 0)
        self.assertEqual(SatCanceladoORM.objects.filter(rfc="AAA010101AAA").count(), 2)

    def test_identical_duplicate_rows_imported_once(self):
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
        with mock.patch.object(
            sat_views, "get_sat_sync_runner", return_value=_make_sync_runner(csv_bytes)
        ):
            resp = self.admin_client.post("/api/v1/sat/sync")
        status_resp = self.admin_client.get(
            f"/api/v1/sat/sync/{resp.data['history_id']}"
        )
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp.data["status"], "completed")
        self.assertEqual(status_resp.data["record_number"], 1)
        self.assertEqual(status_resp.data["omitted_number"], 1)
        self.assertEqual(SatCanceladoORM.objects.filter(rfc="AOAC580716NP7").count(), 1)

    def test_cooldown_skips_second_run_and_force_bypasses(self):
        csv_bytes = make_csv(
            [
                [
                    "AAA010101AAA",
                    "EMPRESA UNO SA DE CV",
                    "M",
                    "CANCELADOS",
                    "28/05/2019",
                    "0",
                    "20/08/2019",
                    "BAJA CALIFORNIA SUR",
                ]
            ]
        )
        runner = _make_sync_runner(csv_bytes)
        with mock.patch.object(sat_views, "get_sat_sync_runner", return_value=runner):
            first = self.admin_client.post("/api/v1/sat/sync")
            self.assertEqual(first.status_code, 202)

            # within the 30-minute cooldown window -> skipped
            second = self.admin_client.post("/api/v1/sat/sync")
            self.assertEqual(second.status_code, 200, second.content)
            self.assertEqual(second.data["status"], "skipped")
            self.assertEqual(second.data["reason"], "cooldown")

            # force bypasses the cooldown
            forced = self.admin_client.post("/api/v1/sat/sync?force=true")
            self.assertEqual(forced.status_code, 202, forced.content)

    def test_download_failure_records_error_status(self):
        runner = _make_sync_runner(b"", raise_download=SatDownloadError("SAT is down"))
        with mock.patch.object(sat_views, "get_sat_sync_runner", return_value=runner):
            resp = self.admin_client.post("/api/v1/sat/sync")
        self.assertEqual(resp.status_code, 202)
        status_resp = self.admin_client.get(
            f"/api/v1/sat/sync/{resp.data['history_id']}"
        )
        self.assertEqual(status_resp.data["status"], "error")

    def test_in_progress_returns_conflict(self):
        SatHistoryORM.objects.create(
            started_at=utcnow(), status="processing", user=self.admin
        )
        runner = _make_sync_runner(make_csv([]))
        with mock.patch.object(sat_views, "get_sat_sync_runner", return_value=runner):
            resp = self.admin_client.post("/api/v1/sat/sync")
        self.assertEqual(resp.status_code, 409, resp.content)
        self.assertIn("history_id", resp.data)

    def test_status_404_for_unknown_history(self):
        resp = self.admin_client.get(f"/api/v1/sat/sync/{uuid4()}")
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------ #
    # History list
    # ------------------------------------------------------------------ #
    def test_history_list_paginated_and_ordered(self):
        base = utcnow()
        for index in range(45):
            SatHistoryORM.objects.create(
                started_at=base - timedelta(minutes=index),
                completed_at=base - timedelta(minutes=index),
                status="completed",
                file_hash=f"hash-{index:02d}",
                processing_time=1.0,
                record_number=index,
                omitted_number=0,
                user=self.admin,
            )

        page1 = self.admin_client.get("/api/v1/sat/history").data
        self.assertEqual(page1["count"], 45)
        self.assertEqual(len(page1["results"]), 20)
        self.assertIsNotNone(page1["next"])
        self.assertIsNone(page1["previous"])
        # newest first (started_at descending)
        timestamps = [item["started_at"] for item in page1["results"]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

        page3 = self.admin_client.get("/api/v1/sat/history", {"page": 3}).data
        self.assertEqual(len(page3["results"]), 5)
        self.assertIsNone(page3["next"])
        self.assertIsNotNone(page3["previous"])

        # invalid page -> 400 (validation error from the query DTO)
        self.assertEqual(
            self.admin_client.get("/api/v1/sat/history", {"page": 0}).status_code, 400
        )
