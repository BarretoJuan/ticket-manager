"""Pure domain unit tests — business rules live in the entities."""

import unittest
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from domain.entities.booking import Booking
from domain.entities.event import Event
from domain.entities.log_entry import LogEntry, LogType
from domain.entities.user import Role, User
from domain.exceptions import (
    EventCapacityError,
    EventCodeFormatError,
    EventNameLengthError,
    EventNotInFutureError,
    EventPriceError,
    InsufficientTicketsError,
    InvalidEmailError,
    InvalidTicketQuantityError,
    LogValidationError,
    UserValidationError,
)
from domain.utils import utcnow


def make_event(**overrides):
    defaults = dict(
        id=uuid4(),
        created_at=utcnow(),
        updated_at=utcnow(),
        deleted_at=None,
        name="Summer Concert",
        code="EVT-2026-MX",
        date=utcnow() + timedelta(days=30),
        total_capacity=100,
        available_tickets=100,
        ticket_price=Decimal("45.50"),
    )
    defaults.update(overrides)
    return Event(**defaults)


class EventValidationTests(unittest.TestCase):
    def test_valid_event_passes(self):
        make_event().validate()  # should not raise

    def test_name_too_short(self):
        with self.assertRaises(EventNameLengthError):
            make_event(name="Jazz").validate()

    def test_name_too_long(self):
        with self.assertRaises(EventNameLengthError):
            make_event(name="x" * 101).validate()

    def test_invalid_code(self):
        for bad in ["EVT-26-MX", "EVT-2026-MX!"]:
            with self.subTest(bad=bad), self.assertRaises(EventCodeFormatError):
                make_event(code=bad).validate()

    def test_code_regex_accepts_valid(self):
        make_event(code="EVT-2023-US").validate()

    def test_date_must_be_future(self):
        with self.assertRaises(EventNotInFutureError):
            make_event(date=utcnow() - timedelta(days=1)).validate()

    def test_capacity_must_be_positive(self):
        with self.assertRaises(EventCapacityError):
            make_event(total_capacity=0, available_tickets=0).validate()

    def test_available_tickets_within_range(self):
        with self.assertRaises(EventCapacityError):
            make_event(available_tickets=-1).validate()
        with self.assertRaises(EventCapacityError):
            make_event(available_tickets=101).validate()

    def test_price_must_be_positive(self):
        with self.assertRaises(EventPriceError):
            make_event(ticket_price=Decimal("0.00")).validate()

    def test_deleted_event_does_not_require_future_date(self):
        make_event(date=utcnow() - timedelta(days=1), deleted_at=utcnow()).validate()

    def test_can_book_and_with_booking(self):
        event = make_event(total_capacity=5, available_tickets=5)
        self.assertTrue(event.can_book(5))
        self.assertFalse(event.can_book(6))
        updated = event.with_booking(2)
        self.assertEqual(updated.available_tickets, 3)
        with self.assertRaises(InsufficientTicketsError):
            event.with_booking(6)


class BookingValidationTests(unittest.TestCase):
    def test_quantity_between_1_and_5(self):
        valid = Booking(
            id=uuid4(), created_at=utcnow(), updated_at=utcnow(), deleted_at=None,
            event_id=uuid4(), user_id=uuid4(), ticket_quantity=3,
        )
        valid.validate()

    def test_quantity_zero_or_six_rejected(self):
        for q in (0, 6):
            with self.subTest(q=q), self.assertRaises(InvalidTicketQuantityError):
                Booking(
                    id=uuid4(), created_at=utcnow(), updated_at=utcnow(), deleted_at=None,
                    event_id=uuid4(), user_id=uuid4(), ticket_quantity=q,
                ).validate()


class UserValidationTests(unittest.TestCase):
    def make_user(self, **overrides):
        defaults = dict(
            id=uuid4(), created_at=utcnow(), updated_at=utcnow(), deleted_at=None,
            email="user@example.com", last_login_at=None, role=Role.USER,
            password_hash="hash",
        )
        defaults.update(overrides)
        return User(**defaults)

    def test_valid_user(self):
        self.make_user().validate()

    def test_invalid_email(self):
        with self.assertRaises(InvalidEmailError):
            self.make_user(email="nope").validate()

    def test_invalid_role(self):
        with self.assertRaises(UserValidationError):
            self.make_user(role="SUPERUSER").validate()

    def test_empty_hash(self):
        with self.assertRaises(UserValidationError):
            self.make_user(password_hash="").validate()


class LogEntryValidationTests(unittest.TestCase):
    def test_valid(self):
        LogEntry(
            id=uuid4(), created_at=utcnow(), type=LogType.INFO,
            name="test", content="hello",
        ).validate()

    def test_invalid_type(self):
        with self.assertRaises(LogValidationError):
            LogEntry(
                id=uuid4(), created_at=utcnow(), type="debug",
                name="test", content="hello",
            ).validate()


if __name__ == "__main__":
    unittest.main()