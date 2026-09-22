"""Mappers between Django ORM rows and pure domain entities."""

from domain.entities.booking import Booking
from domain.entities.event import Event
from domain.entities.log_entry import LogEntry
from domain.entities.user import User

from infrastructure.orm.models import BookingORM, EventORM, LogORM, UserORM


# --------------------------------------------------------------------------- #
# Event
# --------------------------------------------------------------------------- #
def event_orm_to_domain(row: EventORM) -> Event:
    return Event(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        name=row.name,
        code=row.code,
        date=row.date,
        total_capacity=row.total_capacity,
        available_tickets=row.available_tickets,
        ticket_price=row.ticket_price,
    )


def event_domain_to_orm(event: Event) -> dict:
    return {
        "id": event.id,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "deleted_at": event.deleted_at,
        "name": event.name,
        "code": event.code,
        "date": event.date,
        "total_capacity": event.total_capacity,
        "available_tickets": event.available_tickets,
        "ticket_price": event.ticket_price,
    }


# --------------------------------------------------------------------------- #
# User
# --------------------------------------------------------------------------- #
def user_orm_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        email=row.email,
        last_login_at=row.last_login_at,
        role=row.role,
        password_hash=row.password,
    )


def user_domain_to_orm(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "password": user.password_hash,
        "role": user.role,
        "last_login_at": user.last_login_at,
        "deleted_at": user.deleted_at,
    }


# --------------------------------------------------------------------------- #
# Booking
# --------------------------------------------------------------------------- #
def booking_orm_to_domain(row: BookingORM) -> Booking:
    return Booking(
        id=row.id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        event_id=row.event_id,
        user_id=row.user_id,
        ticket_quantity=row.ticket_quantity,
    )


# --------------------------------------------------------------------------- #
# Log
# --------------------------------------------------------------------------- #
def log_orm_to_domain(row: LogORM) -> LogEntry:
    return LogEntry(
        id=row.id,
        created_at=row.created_at,
        type=row.type,
        name=row.name,
        content=row.content,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        endpoint=row.endpoint,
        http_method=row.http_method,
        status_code=row.status_code,
        stack_trace=row.stack_trace,
        user_id=row.user_id,
        event_id=row.event_id,
    )