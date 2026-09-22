"""Use case tests with fake (in-memory) repositories — no database required.

Verifies that business logic lives in the use cases + domain and that use
cases depend only on repository *ports* (dependency injection).
"""

import unittest
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from application.use_cases.book_ticket import BookTicket
from application.use_cases.create_event import CreateEvent
from application.use_cases.delete_event import DeleteEvent
from application.use_cases.list_events import ListEvents
from application.use_cases.login_user import LoginUser
from application.use_cases.register_user import RegisterUser
from application.use_cases.update_event import UpdateEvent

from domain.entities.booking import Booking
from domain.entities.event import Event
from domain.entities.user import Role
from domain.exceptions import (
    EmailAlreadyExistsError,
    EventCodeAlreadyExistsError,
    EventNotFoundError,
    InsufficientTicketsError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidTicketQuantityError,
    WeakPasswordError,
)
from domain.repositories.booking_repository import BookingRepository
from domain.repositories.event_repository import (
    EventPage,
    EventQuery,
    EventRepository,
)
from domain.repositories.log_repository import LogRepository
from domain.repositories.user_repository import UserRepository
from domain.services.password_service import PasswordService
from domain.utils import utcnow


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeEventRepository(EventRepository):
    def __init__(self):
        self.events: dict = {}

    def create(self, event):
        self.events[event.id] = event
        return event

    def get_by_id(self, event_id):
        event = self.events.get(event_id)
        return event if event and event.deleted_at is None else None

    def code_exists(self, code):
        return any(e.code == code for e in self.events.values())

    def list(self, query: EventQuery = EventQuery()):
        matches = [
            e
            for e in self.events.values()
            if e.deleted_at is None
            and (query.code is None or e.code == query.code)
            and (query.name is None or query.name.lower() in e.name.lower())
            and (query.date_from is None or e.date >= query.date_from)
            and (query.date_to is None or e.date <= query.date_to)
            and (
                query.availability is None
                or (query.availability == "available" and e.available_tickets > 0)
                or (query.availability == "sold_out" and e.available_tickets == 0)
            )
        ]
        matches.sort(key=lambda e: e.date)
        page = matches[query.offset : query.offset + query.limit]
        return EventPage(items=page, total=len(matches))

    def save(self, event):
        self.events[event.id] = event
        return event

    def soft_delete(self, event_id):
        self.events[event_id] = replace(self.events[event_id], deleted_at=utcnow())


class FakeBookingRepository(BookingRepository):
    def __init__(self, events: FakeEventRepository):
        self.bookings = []
        self.events = events

    def create_booking_atomic(self, *, event_id, user_id, quantity):
        event = self.events.events.get(event_id)
        if event is None or event.deleted_at is not None:
            raise EventNotFoundError("event not found")
        if event.available_tickets < quantity:
            raise InsufficientTicketsError("not enough available tickets")
        updated = event.with_booking(quantity)
        self.events.events[event_id] = updated
        booking = Booking(
            id=uuid4(),
            created_at=utcnow(),
            updated_at=utcnow(),
            deleted_at=None,
            event_id=event_id,
            user_id=user_id,
            ticket_quantity=quantity,
        )
        self.bookings.append(booking)
        return booking


class FakeUserRepository(UserRepository):
    def __init__(self):
        self.users: dict = {}

    def create(self, user):
        self.users[user.id] = user
        return user

    def get_by_email(self, email):
        for u in self.users.values():
            if u.email == email and u.deleted_at is None:
                return u
        return None

    def get_by_id(self, user_id):
        return self.users.get(user_id)

    def email_exists(self, email):
        return any(u.email == email for u in self.users.values())

    def update(self, user):
        self.users[user.id] = user
        return user


class FakePasswordService(PasswordService):
    def hash(self, raw):
        return f"hash:{raw}"

    def verify(self, raw, hashed):
        return hashed == f"hash:{raw}"


class FakeLogRepository(LogRepository):
    def __init__(self):
        self.entries = []

    def create(self, entry):
        self.entries.append(entry)
        return entry


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def future_date(days=30):
    return utcnow() + timedelta(days=days)


def new_event_input(**overrides):
    data = dict(
        name="Rock Festival",
        code="EVT-2026-ES",
        date=future_date(),
        total_capacity=50,
        ticket_price=Decimal("25.00"),
    )
    data.update(overrides)
    return data


# --------------------------------------------------------------------------- #
# RegisterUser / LoginUser
# --------------------------------------------------------------------------- #
class RegisterAndLoginTests(unittest.TestCase):
    def setUp(self):
        self.users = FakeUserRepository()
        self.password = FakePasswordService()
        self.register = RegisterUser(self.users, self.password)
        self.login = LoginUser(self.users, self.password)

    def test_register_creates_user_role(self):
        user = self.register.execute(email="A@Example.com", password="password123")
        self.assertEqual(user.email, "a@example.com")  # normalized
        self.assertEqual(user.role, Role.USER)
        self.assertTrue(user.password_hash.startswith("hash:"))

    def test_register_duplicate_email(self):
        self.register.execute(email="a@example.com", password="password123")
        with self.assertRaises(EmailAlreadyExistsError):
            self.register.execute(email="a@example.com", password="password123")

    def test_register_invalid_email(self):
        with self.assertRaises(InvalidEmailError):
            self.register.execute(email="nope", password="password123")

    def test_register_weak_password(self):
        with self.assertRaises(WeakPasswordError):
            self.register.execute(email="a@example.com", password="short")

    def test_login_success_updates_last_login(self):
        self.register.execute(email="a@example.com", password="password123")
        user = self.login.execute(email="a@example.com", password="password123")
        self.assertIsNotNone(user.last_login_at)

    def test_login_wrong_password(self):
        self.register.execute(email="a@example.com", password="password123")
        with self.assertRaises(InvalidCredentialsError):
            self.login.execute(email="a@example.com", password="wrong")


# --------------------------------------------------------------------------- #
# Event CRUD use cases
# --------------------------------------------------------------------------- #
class EventUseCaseTests(unittest.TestCase):
    def setUp(self):
        self.events = FakeEventRepository()
        self.logs = FakeLogRepository()
        self.create = CreateEvent(self.events, self.logs)
        self.update = UpdateEvent(self.events, self.logs)
        self.delete = DeleteEvent(self.events, self.logs)
        self.list = ListEvents(self.events)

    def test_create_event_initializes_available_tickets_to_capacity(self):
        event = self.create.execute(**new_event_input())
        self.assertEqual(event.available_tickets, event.total_capacity)
        self.assertEqual(len(self.logs.entries), 1)
        self.assertEqual(self.logs.entries[0].name, "event.created")

    def test_create_event_duplicate_code(self):
        self.create.execute(**new_event_input(code="EVT-2026-ES"))
        with self.assertRaises(EventCodeAlreadyExistsError):
            self.create.execute(**new_event_input(code="EVT-2026-ES", name="Other"))

    def test_create_event_non_future_date_rejected(self):
        from domain.exceptions import EventNotInFutureError

        with self.assertRaises(EventNotInFutureError):
            self.create.execute(**new_event_input(date=utcnow() - timedelta(days=1)))

    def test_update_event_capacity_increases_available(self):
        event = self.create.execute(**new_event_input(total_capacity=10))
        updated = self.update.execute(event_id=event.id, total_capacity=20)
        self.assertEqual(updated.total_capacity, 20)
        self.assertEqual(updated.available_tickets, 20)

    def test_update_event_cannot_shrink_below_sold(self):
        from domain.exceptions import EventCapacityError

        event = self.create.execute(**new_event_input(total_capacity=10))
        # skip the atomic repo in this fake: reduce manually
        event = self.events.save(event.with_booking(4))
        with self.assertRaises(EventCapacityError):
            self.update.execute(event_id=event.id, total_capacity=2)

    def test_delete_event_soft_deletes(self):
        event = self.create.execute(**new_event_input())
        self.delete.execute(event_id=event.id)
        self.assertIsNone(self.events.get_by_id(event.id))  # excluded from live queries
        self.assertEqual(len(self.logs.entries), 2)  # created + deleted

    def test_delete_missing_event(self):
        with self.assertRaises(EventNotFoundError):
            self.delete.execute(event_id=uuid4())

    def test_list_excludes_deleted(self):
        a = self.create.execute(**new_event_input(code="EVT-2026-ES"))
        self.create.execute(**new_event_input(code="EVT-2026-MX"))
        self.delete.execute(event_id=a.id)
        codes = [e.code for e in self.list.execute(query=EventQuery()).items]
        self.assertEqual(codes, ["EVT-2026-MX"])

    def test_list_filters_by_name(self):
        self.create.execute(**new_event_input(code="EVT-2026-ES", name="Rock Festival"))
        self.create.execute(**new_event_input(code="EVT-2026-MX", name="Jazz Night"))
        result = self.list.execute(query=EventQuery(name="ROCK"))
        self.assertEqual([e.code for e in result.items], ["EVT-2026-ES"])

    def test_list_filters_by_availability(self):
        event = self.create.execute(
            **new_event_input(code="EVT-2026-ES", total_capacity=10)
        )
        self.events.save(event.with_booking(10))  # sell the event out
        self.create.execute(**new_event_input(code="EVT-2026-MX", total_capacity=10))

        sold = self.list.execute(query=EventQuery(availability="sold_out"))
        self.assertEqual([e.code for e in sold.items], ["EVT-2026-ES"])

        available = self.list.execute(query=EventQuery(availability="available"))
        self.assertEqual([e.code for e in available.items], ["EVT-2026-MX"])

    def test_list_paginates_and_reports_total(self):
        for i in range(25):
            code = f"EVT-2026-{chr(65 + i % 26)}{chr(65 + i // 26)}"
            self.create.execute(**new_event_input(code=code))

        first = self.list.execute(query=EventQuery(limit=20))
        self.assertEqual(len(first.items), 20)
        self.assertEqual(first.total, 25)

        second = self.list.execute(query=EventQuery(offset=20, limit=20))
        self.assertEqual(len(second.items), 5)
        self.assertEqual(second.total, 25)


# --------------------------------------------------------------------------- #
# BookTicket
# --------------------------------------------------------------------------- #
class BookTicketTests(unittest.TestCase):
    def setUp(self):
        self.events = FakeEventRepository()
        self.bookings = FakeBookingRepository(self.events)
        self.logs = FakeLogRepository()
        self.book = BookTicket(self.bookings, self.events, self.logs)
        self.user_id = uuid4()
        self.event = self.events.create(
            Event(
                id=uuid4(),
                created_at=utcnow(),
                updated_at=utcnow(),
                deleted_at=None,
                name="Concert",
                code="EVT-2026-US",
                date=future_date(),
                total_capacity=5,
                available_tickets=5,
                ticket_price=Decimal("10.00"),
            )
        )

    def test_successful_booking(self):
        booking = self.book.execute(
            event_id=self.event.id, user_id=self.user_id, quantity=2
        )
        self.assertEqual(booking.ticket_quantity, 2)
        self.assertEqual(self.events.get_by_id(self.event.id).available_tickets, 3)
        self.assertEqual([e.name for e in self.logs.entries], ["booking.created"])

    def test_booking_exceeding_capacity_rejected(self):
        self.book.execute(event_id=self.event.id, user_id=self.user_id, quantity=5)
        with self.assertRaises(InsufficientTicketsError):
            self.book.execute(event_id=self.event.id, user_id=self.user_id, quantity=1)
        self.assertEqual(
            [e.name for e in self.logs.entries],
            ["booking.created", "booking.rejected"],
        )

    def test_booking_quantity_out_of_range(self):
        for q in (0, 6):
            with self.subTest(q=q), self.assertRaises(InvalidTicketQuantityError):
                self.book.execute(
                    event_id=self.event.id, user_id=self.user_id, quantity=q
                )

    def test_booking_missing_event(self):
        with self.assertRaises(EventNotFoundError):
            self.book.execute(event_id=uuid4(), user_id=self.user_id, quantity=1)


if __name__ == "__main__":
    unittest.main()
