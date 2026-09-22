"""Composition root: wires use cases to infrastructure implementations (DI).

Use cases receive their repository implementations through their constructors.
"""

from application.use_cases.book_ticket import BookTicket
from application.use_cases.create_event import CreateEvent
from application.use_cases.delete_event import DeleteEvent
from application.use_cases.list_events import ListEvents
from application.use_cases.login_user import LoginUser
from application.use_cases.register_user import RegisterUser
from application.use_cases.update_event import UpdateEvent

from infrastructure.repositories.django_booking_repository import (
    DjangoBookingRepository,
)
from infrastructure.repositories.django_event_repository import DjangoEventRepository
from infrastructure.repositories.django_log_repository import DjangoLogRepository
from infrastructure.repositories.django_password_service import DjangoPasswordService
from infrastructure.repositories.django_user_repository import DjangoUserRepository

# --------------------------------------------------------------------------- #
# Repository singletons
# --------------------------------------------------------------------------- #
_event_repository = DjangoEventRepository()
_booking_repository = DjangoBookingRepository()
_user_repository = DjangoUserRepository()
_log_repository = DjangoLogRepository()
_password_service = DjangoPasswordService()


# --------------------------------------------------------------------------- #
# Use cases (dependencies injected)
# --------------------------------------------------------------------------- #
def get_register_user_use_case() -> RegisterUser:
    return RegisterUser(_user_repository, _password_service)


def get_login_user_use_case() -> LoginUser:
    return LoginUser(_user_repository, _password_service)


def get_create_event_use_case() -> CreateEvent:
    return CreateEvent(_event_repository, _log_repository)


def get_update_event_use_case() -> UpdateEvent:
    return UpdateEvent(_event_repository, _log_repository)


def get_delete_event_use_case() -> DeleteEvent:
    return DeleteEvent(_event_repository, _log_repository)


def get_list_events_use_case() -> ListEvents:
    return ListEvents(_event_repository)


def get_book_ticket_use_case() -> BookTicket:
    return BookTicket(_booking_repository, _event_repository, _log_repository)


__all__ = [
    "get_register_user_use_case",
    "get_login_user_use_case",
    "get_create_event_use_case",
    "get_update_event_use_case",
    "get_delete_event_use_case",
    "get_list_events_use_case",
    "get_book_ticket_use_case",
]