"""Management command: idempotently seed demo data for the Ticket Manager.

Creates an admin, demo users, upcoming events, and a few bookings by going
through the real application use cases (domain validation, password hashing,
atomic capacity checks, audit logs). Safe to run any number of times: existing
users/events are left untouched and bookings are only created for events that
were freshly created in the current run.

Configuration via environment variables (all optional):

  SEED_ENABLED          whether to seed at all          (default: true)
  SEED_ADMIN_EMAIL      admin account email             (default: admin@example.com)
  SEED_ADMIN_PASSWORD   admin account password          (default: Admin12345!)
  SEED_DEMO_USERS       comma-separated emails
                        (default: alice@example.com,bob@example.com)
  SEED_BOOKINGS         whether to create demo bookings (default: true)
"""

import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand

from domain.exceptions import EmailAlreadyExistsError, EventCodeAlreadyExistsError
from domain.utils import utcnow
from infrastructure.orm.models import UserORM, UserRole
from presentation.di import (
    get_book_ticket_use_case,
    get_create_event_use_case,
    get_register_user_use_case,
)

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "Admin12345!"
DEFAULT_DEMO_USERS = "alice@example.com,bob@example.com"
DEMO_USER_PASSWORD = "Demo12345!"

# (name, code tag, days from now, total capacity, ticket price)
EVENTS = [
    ("Rock Festival", "RO", 7, 200, "25.00"),
    ("Jazz Night", "JZ", 14, 80, "40.00"),
    ("Tech Summit", "TS", 30, 500, "120.00"),
    ("Comedy Show", "CM", 45, 150, "30.00"),
]

# Number of tickets booked per freshly-created event, keyed by code tag.
BOOKING_QUANTITIES = {"RO": 2, "JZ": 1, "TS": 3, "CM": 2}


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


class Command(BaseCommand):
    help = (
        "Seed an admin, demo users, upcoming events, and a few bookings (idempotent)."
    )

    def handle(self, *args, **options):
        if not _env_bool("SEED_ENABLED", True):
            self.stdout.write("Seeding skipped (SEED_ENABLED=false).")
            return

        admin_email = _env_str("SEED_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL).lower()
        admin_password = _env_str("SEED_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
        demo_emails = [
            e.strip().lower()
            for e in _env_str("SEED_DEMO_USERS", DEFAULT_DEMO_USERS).split(",")
            if e.strip()
        ]
        seed_bookings = _env_bool("SEED_BOOKINGS", True)

        admin_created = self._ensure_admin(admin_email, admin_password)
        user_ids = self._seed_users(demo_emails)
        new_events = self._seed_events()
        bookings_created = (
            self._seed_bookings(user_ids, new_events)
            if seed_bookings and user_ids and new_events
            else 0
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeding done: admin={0} ({1}), users={2}, "
                "new_events={3}, new_bookings={4}".format(
                    admin_email,
                    "created" if admin_created else "already present",
                    len(user_ids),
                    len(new_events),
                    bookings_created,
                )
            )
        )

    def _ensure_admin(self, email: str, password: str) -> bool:
        """Create the admin, or promote an existing account. Returns created."""
        user = UserORM.objects.filter(email=email).first()
        if user is None:
            user = UserORM(email=email, role=UserRole.ADMIN, is_active=True)
            user.set_password(password)
            user.save()
            self.stdout.write(f"  admin {email} created")
            return True

        fields = []
        if user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            fields.append("role")
        if not user.is_active or user.deleted_at is not None:
            user.is_active = True
            user.deleted_at = None
            fields.extend(["is_active", "deleted_at"])
        if fields:
            user.save(update_fields=fields)
        self.stdout.write(f"  admin {email} already present")
        return False

    def _seed_users(self, emails: list[str]) -> dict[str, object]:
        """Register demo users through the use case; return email -> user id."""
        register = get_register_user_use_case()
        user_ids = {}
        for email in emails:
            try:
                user = register.execute(email=email, password=DEMO_USER_PASSWORD)
                user_ids[email] = user.id
                self.stdout.write(f"  user {email} created")
            except EmailAlreadyExistsError:
                user_id = UserORM.objects.values_list("id", flat=True).get(email=email)
                user_ids[email] = user_id
                self.stdout.write(f"  user {email} already exists")
        return user_ids

    def _seed_events(self) -> list[object]:
        """Create upcoming events through the use case; return newly created."""
        create_event = get_create_event_use_case()
        now = utcnow()
        created = []
        for name, tag, days, capacity, price in EVENTS:
            code = f"EVT-{now.year:04d}-{tag}"
            try:
                event = create_event.execute(
                    name=name,
                    code=code,
                    date=now + timedelta(days=days),
                    total_capacity=capacity,
                    ticket_price=Decimal(price),
                )
                created.append(event)
                self.stdout.write(f"  event {code} created")
            except EventCodeAlreadyExistsError:
                self.stdout.write(f"  event {code} already exists")
        return created

    def _seed_bookings(self, user_ids: dict, events: list) -> int:
        """Book seats on each freshly-created event from a demo user."""
        book_ticket = get_book_ticket_use_case()
        emails = list(user_ids)
        count = 0
        for index, event in enumerate(events):
            tag = event.code[-2:]
            quantity = BOOKING_QUANTITIES.get(tag, 1)
            email = emails[index % len(emails)]
            book_ticket.execute(
                event_id=event.id,
                user_id=user_ids[email],
                quantity=quantity,
            )
            count += 1
            self.stdout.write(f"  booking {event.code} x{quantity} by {email}")
        return count
