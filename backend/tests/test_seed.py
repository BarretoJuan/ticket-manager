"""Tests for the idempotent ``seed`` management command."""

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from infrastructure.orm.models import BookingORM, EventORM, UserORM, UserRole

SEED_ENV = {
    "SEED_ENABLED": "true",
    "SEED_ADMIN_EMAIL": "admin@example.com",
    "SEED_ADMIN_PASSWORD": "Admin12345!",
    "SEED_DEMO_USERS": "alice@example.com,bob@example.com",
    "SEED_BOOKINGS": "true",
}


def call_seed():
    """Run seed with a fixed env so local .env overrides can't leak in."""
    with patch.dict("os.environ", SEED_ENV, clear=False):
        call_command("seed")


# Seeded bookings trigger the confirmation e-mail through the real DI graph;
# isolate it with the local-memory backend so tests never attempt SMTP.
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SeedCommandTests(TestCase):
    def test_seed_creates_demo_data(self):
        call_seed()
        self.assertTrue(
            UserORM.objects.filter(
                email="admin@example.com", role=UserRole.ADMIN
            ).exists()
        )
        for email in ("alice@example.com", "bob@example.com"):
            self.assertTrue(UserORM.objects.filter(email=email).exists())
        # Events follow the 4-element default EVENTS table.
        self.assertGreaterEqual(EventORM.objects.count(), 4)
        self.assertGreater(BookingORM.objects.count(), 0)

    def test_seed_is_idempotent(self):
        call_seed()
        users, events, bookings = (
            UserORM.objects.count(),
            EventORM.objects.count(),
            BookingORM.objects.count(),
        )
        call_seed()
        self.assertEqual(UserORM.objects.count(), users)
        self.assertEqual(EventORM.objects.count(), events)
        self.assertEqual(BookingORM.objects.count(), bookings)

    def test_seed_respects_seed_enabled_false(self):
        with patch.dict("os.environ", {"SEED_ENABLED": "false"}, clear=False):
            call_command("seed")
        self.assertEqual(UserORM.objects.count(), 0)
        self.assertEqual(EventORM.objects.count(), 0)
        self.assertEqual(BookingORM.objects.count(), 0)

    def test_seed_respects_seed_bookings_false(self):
        with patch.dict("os.environ", {**SEED_ENV, "SEED_BOOKINGS": "false"}):
            call_command("seed")
        self.assertGreater(UserORM.objects.count(), 0)
        self.assertGreater(EventORM.objects.count(), 0)
        self.assertEqual(BookingORM.objects.count(), 0)
