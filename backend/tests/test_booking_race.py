"""Overbooking race condition test.

Proves that concurrent bookings never exceed the event capacity, thanks to
PostgreSQL pessimistic row-level locking (``SELECT ... FOR UPDATE``) inside
``transaction.atomic()`` in ``DjangoBookingRepository.create_booking_atomic``.

Requires a real PostgreSQL test database (Django's test runner creates one).
"""

from concurrent.futures import ThreadPoolExecutor

from django.db import connections
from django.test import TransactionTestCase

from application.use_cases.book_ticket import BookTicket

from domain.exceptions import InsufficientTicketsError
from domain.utils import utcnow

from infrastructure.orm.models import BookingORM, EventORM, UserORM
from infrastructure.repositories.django_booking_repository import (
    DjangoBookingRepository,
)
from infrastructure.repositories.django_event_repository import DjangoEventRepository


class BookingRaceTests(TransactionTestCase):
    """TransactionTestCase: real commits, no test-transaction wrapping."""

    def _seed_event(self, capacity: int):
        return EventORM.objects.create(
            name="Race Event",
            code=f"EVT-{capacity:04d}-US",
            date=utcnow(),
            total_capacity=capacity,
            available_tickets=capacity,
            ticket_price="10.00",
        )

    @staticmethod
    def _book_worker(*, use_case, event_id, user_id):
        """Run one booking attempt in a worker thread and close its connection."""
        try:
            return use_case.execute(event_id=event_id, user_id=user_id, quantity=1)
        finally:
            connections.close_all()

    def test_concurrent_bookings_never_oversell(self):
        capacity = 5
        event = self._seed_event(capacity)
        user = UserORM.objects.create_user(
            email="racer@example.com", password="pass12345"
        )

        event_repo = DjangoEventRepository()
        booking_repo = DjangoBookingRepository()
        use_case = BookTicket(booking_repo, event_repo)

        attempts = 30  # many more than the capacity
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [
                pool.submit(
                    self._book_worker,
                    use_case=use_case,
                    event_id=event.id,
                    user_id=user.id,
                )
                for _ in range(attempts)
            ]
            ok = 0
            rejected = 0
            for f in futures:
                try:
                    f.result()
                    ok += 1
                except InsufficientTicketsError:
                    rejected += 1

        # Close per-thread DB connections so the test DB can be dropped later.
        connections.close_all()

        # Exactly `capacity` bookings must survive the race...
        self.assertEqual(ok, capacity)
        self.assertEqual(rejected, attempts - capacity)

        # ...with the event's available_tickets never going negative...
        event.refresh_from_db()
        self.assertEqual(event.available_tickets, 0)

        # ...and exactly `capacity` booking rows persisted.
        self.assertEqual(BookingORM.objects.filter(event=event).count(), capacity)

    def test_single_booking_many_tickets_respects_capacity(self):
        event = self._seed_event(4)
        user = UserORM.objects.create_user(
            email="multi@example.com", password="pass12345"
        )

        event_repo = DjangoEventRepository()
        booking_repo = DjangoBookingRepository()
        use_case = BookTicket(booking_repo, event_repo)

        use_case.execute(event_id=event.id, user_id=user.id, quantity=4)
        event.refresh_from_db()
        self.assertEqual(event.available_tickets, 0)

        with self.assertRaises(InsufficientTicketsError):
            use_case.execute(event_id=event.id, user_id=user.id, quantity=1)
