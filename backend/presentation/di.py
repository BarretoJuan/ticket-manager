"""Composition root: wires use cases to infrastructure implementations (DI).

Use cases receive their repository implementations through their constructors.
"""

from django.conf import settings

from application.services.booking_notifier import BookingNotifier
from application.services.sat_sync_runner import SatSyncRunner
from application.use_cases.book_ticket import BookTicket
from application.use_cases.create_event import CreateEvent
from application.use_cases.delete_event import DeleteEvent
from application.use_cases.list_events import ListEvents
from application.use_cases.list_sat_history import SatListHistory
from application.use_cases.login_user import LoginUser
from application.use_cases.register_user import RegisterUser
from application.use_cases.sat_sync import SatSync
from application.use_cases.update_event import UpdateEvent

from infrastructure.repositories.django_booking_repository import (
    DjangoBookingRepository,
)
from infrastructure.repositories.django_event_repository import DjangoEventRepository
from infrastructure.repositories.django_log_repository import DjangoLogRepository
from infrastructure.repositories.django_password_service import DjangoPasswordService
from infrastructure.repositories.django_sat_repository import DjangoSatRepository
from infrastructure.repositories.django_user_repository import DjangoUserRepository
from infrastructure.services.django_email_service import DjangoEmailService
from infrastructure.services.http_sat_data_service import HttpSatDataService
from infrastructure.services.pillow_qr_service import PillowQrCodeGenerator

# --------------------------------------------------------------------------- #
# Repository singletons
# --------------------------------------------------------------------------- #
_event_repository = DjangoEventRepository()
_booking_repository = DjangoBookingRepository()
_user_repository = DjangoUserRepository()
_log_repository = DjangoLogRepository()
_password_service = DjangoPasswordService()
_email_service = DjangoEmailService()
_qr_code_generator = PillowQrCodeGenerator()
_booking_notifier = BookingNotifier(
    _user_repository, _email_service, _qr_code_generator
)

# --- SAT sync (art. 69 CFF "Cancelados") ---
_sat_repository = DjangoSatRepository()
_sat_data_service = HttpSatDataService(
    page_url=settings.SAT_PAGE_URL,
    link_text=settings.SAT_LINK_TEXT,
    timeout_seconds=settings.SAT_HTTP_TIMEOUT_SECONDS,
    max_file_bytes=settings.SAT_MAX_FILE_BYTES,
)
_sat_sync_use_case = SatSync(
    _sat_repository,
    _sat_data_service,
    _log_repository,
    cooldown_minutes=settings.SAT_SYNC_COOLDOWN_MINUTES,
    batch_size=settings.SAT_SYNC_BATCH_SIZE,
)
_sat_sync_runner = SatSyncRunner(_sat_sync_use_case)
_sat_list_history_use_case = SatListHistory(_sat_repository)


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
    return BookTicket(
        _booking_repository,
        _event_repository,
        _log_repository,
        _booking_notifier,
    )


def get_sat_sync_runner() -> SatSyncRunner:
    return _sat_sync_runner


def get_sat_sync_use_case() -> SatSync:
    return _sat_sync_use_case


def get_sat_list_history_use_case() -> SatListHistory:
    return _sat_list_history_use_case


__all__ = [
    "get_register_user_use_case",
    "get_login_user_use_case",
    "get_create_event_use_case",
    "get_update_event_use_case",
    "get_delete_event_use_case",
    "get_list_events_use_case",
    "get_book_ticket_use_case",
    "get_sat_sync_runner",
    "get_sat_sync_use_case",
    "get_sat_list_history_use_case",
]
