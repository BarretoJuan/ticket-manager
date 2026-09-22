"""End-to-end API tests (APIClient against the real stack + PostgreSQL)."""

from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from domain.utils import utcnow
from infrastructure.orm.models import EventORM, UserORM

PASSWORD = "Test12345!"


def john_token(client, email="john@example.com"):
    resp = client.post(
        "/api/v1/register", {"email": email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 201, resp.content
    resp = client.post(
        "/api/v1/login", {"email": email, "password": PASSWORD}, format="json"
    )
    assert resp.status_code == 200, resp.content
    return resp.data["access"]


class AuthApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def test_register_login_flow(self):
        resp = self.client.post(
            "/api/v1/register",
            {"email": "alice@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["role"], "USER")

        resp = self.client.post(
            "/api/v1/login",
            {"email": "alice@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_login_wrong_password_is_401(self):
        self.client.post(
            "/api/v1/register",
            {"email": "bob@example.com", "password": PASSWORD},
            format="json",
        )
        resp = self.client.post(
            "/api/v1/login",
            {"email": "bob@example.com", "password": "nope"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_duplicate_email_is_409(self):
        self.client.post(
            "/api/v1/register",
            {"email": "carol@example.com", "password": PASSWORD},
            format="json",
        )
        resp = self.client.post(
            "/api/v1/register",
            {"email": "carol@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(resp.status_code, 409)

    def test_register_rate_limited(self):
        # 10 registers allowed per client IP, 11th is throttled with 429.
        statuses = []
        for i in range(11):
            resp = self.client.post(
                "/api/v1/register",
                {"email": f"limited{i}@example.com", "password": PASSWORD},
                format="json",
            )
            statuses.append(resp.status_code)
        self.assertEqual(statuses[:10], [201] * 10)
        self.assertEqual(statuses[10], 429)

    def test_login_rate_limited(self):
        self.client.post(
            "/api/v1/register",
            {"email": "loginlimited@example.com", "password": PASSWORD},
            format="json",
        )
        # 10 logins allowed per client IP, 11th is throttled with 429.
        statuses = []
        for _ in range(11):
            resp = self.client.post(
                "/api/v1/login",
                {"email": "loginlimited@example.com", "password": PASSWORD},
                format="json",
            )
            statuses.append(resp.status_code)
        self.assertEqual(statuses[:10], [200] * 10)
        self.assertEqual(statuses[10], 429)


class EventAndBookingApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user_client = APIClient()
        self.user_token = john_token(self.user_client)
        self.user_client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.user_token}")

        self.admin = UserORM.objects.create_user(
            email="admin@example.com", password=PASSWORD, role="ADMIN"
        )
        admin_login = APIClient().post(
            "/api/v1/login",
            {"email": "admin@example.com", "password": PASSWORD},
            format="json",
        )
        self.admin_client = APIClient()
        self.admin_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {admin_login.data['access']}"
        )

        self.event_payload = {
            "name": "Tech Conference 2027",
            "code": "EVT-2027-US",
            "date": "2027-06-15T09:00:00Z",
            "total_capacity": 5,
            "ticket_price": "99.90",
        }

    def test_unauthenticated_requests_are_rejected(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/v1/events").status_code, 401)
        self.assertEqual(
            anon.post("/api/v1/events", self.event_payload, format="json").status_code,
            401,
        )

    def test_only_admin_can_create_event(self):
        resp = self.user_client.post(
            "/api/v1/events", self.event_payload, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_creates_event_with_available_equals_capacity(self):
        resp = self.admin_client.post(
            "/api/v1/events", self.event_payload, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["total_capacity"], 5)
        self.assertEqual(resp.data["available_tickets"], 5)

    def test_event_code_must_match_regex(self):
        payload = dict(self.event_payload, code="BAD-CODE")
        resp = self.admin_client.post("/api/v1/events", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_event_code_is_409(self):
        self.admin_client.post("/api/v1/events", self.event_payload, format="json")
        payload = dict(self.event_payload, name="Another event")
        resp = self.admin_client.post("/api/v1/events", payload, format="json")
        self.assertEqual(resp.status_code, 409)

    def test_event_date_must_be_future(self):
        payload = dict(self.event_payload, date="2020-01-01T00:00:00Z")
        resp = self.admin_client.post("/api/v1/events", payload, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_book_flow_and_available_tickets_decrement(self):
        created = self.admin_client.post(
            "/api/v1/events", self.event_payload, format="json"
        )
        event_id = created.data["id"]

        resp = self.user_client.post(
            f"/api/v1/events/{event_id}/book",
            {"ticket_quantity": 3},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["ticket_quantity"], 3)

        listed = self.user_client.get("/api/v1/events").data
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["results"][0]["available_tickets"], 2)

    def test_booking_quantity_limits(self):
        created = self.admin_client.post(
            "/api/v1/events", self.event_payload, format="json"
        )
        event_id = created.data["id"]
        resp = self.user_client.post(
            f"/api/v1/events/{event_id}/book", {"ticket_quantity": 0}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        resp = self.user_client.post(
            f"/api/v1/events/{event_id}/book", {"ticket_quantity": 6}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_booking_capacity_exceeded_is_409(self):
        created = self.admin_client.post(
            "/api/v1/events", self.event_payload, format="json"
        )
        event_id = created.data["id"]
        self.user_client.post(
            f"/api/v1/events/{event_id}/book", {"ticket_quantity": 5}, format="json"
        )
        resp = self.user_client.post(
            f"/api/v1/events/{event_id}/book", {"ticket_quantity": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 409)

    def test_update_and_delete(self):
        created = self.admin_client.post(
            "/api/v1/events", self.event_payload, format="json"
        )
        event_id = created.data["id"]

        resp = self.admin_client.patch(
            f"/api/v1/events/{event_id}", {"total_capacity": 10}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total_capacity"], 10)

        # Regular users cannot update/delete
        self.assertEqual(
            self.user_client.patch(
                f"/api/v1/events/{event_id}", {"total_capacity": 99}, format="json"
            ).status_code,
            403,
        )

        resp = self.admin_client.delete(f"/api/v1/events/{event_id}")
        self.assertEqual(resp.status_code, 204)

        listed = self.user_client.get("/api/v1/events").data
        self.assertEqual(listed["count"], 0)
        self.assertEqual(listed["results"], [])

        # Booking a soft-deleted event -> 404
        resp = self.user_client.post(
            f"/api/v1/events/{event_id}/book", {"ticket_quantity": 1}, format="json"
        )
        self.assertEqual(resp.status_code, 404)

    def test_list_events_paginated_by_20(self):
        now = utcnow()
        for i in range(25):
            EventORM.objects.create(
                name=f"Page Event {i:02d}",
                code=f"EVT-2026-{chr(65 + i // 26)}{chr(65 + i % 26)}",
                date=now + timedelta(days=i + 1),
                total_capacity=100,
                available_tickets=100,
                ticket_price=Decimal("10.00"),
            )

        page1 = self.user_client.get("/api/v1/events").data
        self.assertEqual(page1["count"], 25)
        self.assertEqual(len(page1["results"]), 20)
        self.assertIsNotNone(page1["next"])
        self.assertIsNone(page1["previous"])
        self.assertTrue(page1["next"].endswith("page=2"))

        page2 = self.user_client.get("/api/v1/events", {"page": 2}).data
        self.assertEqual(len(page2["results"]), 5)
        self.assertIsNone(page2["next"])
        self.assertIsNotNone(page2["previous"])
        self.assertTrue(page2["previous"].endswith("page=1"))

    def test_list_events_invalid_page_is_400(self):
        self.assertEqual(
            self.user_client.get("/api/v1/events", {"page": 0}).status_code, 400
        )
        self.assertEqual(
            self.user_client.get("/api/v1/events", {"page": "abc"}).status_code, 400
        )

    def test_list_events_filters_by_name(self):
        self.admin_client.post(
            "/api/v1/events",
            {**self.event_payload, "name": "Rock Festival", "code": "EVT-2027-RK"},
            format="json",
        )
        self.admin_client.post(
            "/api/v1/events",
            {**self.event_payload, "name": "Jazz Night", "code": "EVT-2027-JZ"},
            format="json",
        )

        resp = self.user_client.get("/api/v1/events", {"name": "rock"})
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["name"], "Rock Festival")

    def test_list_events_filters_by_date_range(self):
        for code, date in [
            ("EVT-2027-AA", "2027-06-10T09:00:00Z"),
            ("EVT-2027-AB", "2027-06-20T09:00:00Z"),
            ("EVT-2027-AC", "2027-07-01T09:00:00Z"),
        ]:
            resp = self.admin_client.post(
                "/api/v1/events",
                {**self.event_payload, "code": code, "date": date},
                format="json",
            )
            self.assertEqual(resp.status_code, 201)

        resp = self.user_client.get(
            "/api/v1/events",
            {"date_from": "2027-06-15", "date_to": "2027-06-30"},
        )
        codes = [e["code"] for e in resp.data["results"]]
        self.assertEqual(codes, ["EVT-2027-AB"])

        # Inverted range is rejected with 400.
        resp = self.user_client.get(
            "/api/v1/events",
            {"date_from": "2027-12-01", "date_to": "2027-01-01"},
        )
        self.assertEqual(resp.status_code, 400)

    def test_list_events_filters_by_availability(self):
        self.admin_client.post(
            "/api/v1/events",
            {**self.event_payload, "code": "EVT-2027-SO"},
            format="json",
        )
        created = self.admin_client.post(
            "/api/v1/events",
            {**self.event_payload, "code": "EVT-2027-FU"},
            format="json",
        )
        event_id = created.data["id"]
        for _ in range(5):  # capacity 5 -> sell out
            resp = self.user_client.post(
                f"/api/v1/events/{event_id}/book",
                {"ticket_quantity": 1},
                format="json",
            )
            self.assertEqual(resp.status_code, 201)

        avail = self.user_client.get(
            "/api/v1/events", {"availability": "available"}
        ).data
        self.assertEqual(avail["count"], 1)
        self.assertEqual(avail["results"][0]["code"], "EVT-2027-SO")

        sold = self.user_client.get("/api/v1/events", {"availability": "sold_out"}).data
        self.assertEqual(sold["count"], 1)
        self.assertEqual(sold["results"][0]["code"], "EVT-2027-FU")

        bad = self.user_client.get("/api/v1/events", {"availability": "nope"})
        self.assertEqual(bad.status_code, 400)

    def test_list_events_filters_combine_with_code(self):
        self.admin_client.post(
            "/api/v1/events",
            {**self.event_payload, "name": "Tech One", "code": "EVT-2027-AA"},
            format="json",
        )
        self.admin_client.post(
            "/api/v1/events",
            {**self.event_payload, "name": "Tech Two", "code": "EVT-2027-BB"},
            format="json",
        )
        resp = self.user_client.get(
            "/api/v1/events", {"code": "EVT-2027-AA", "name": "tech"}
        )
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["code"], "EVT-2027-AA")


class HealthApiTests(TestCase):
    def test_health_ok(self):
        resp = APIClient().get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], "ok")
        self.assertEqual(resp.data["database"], "connected")
