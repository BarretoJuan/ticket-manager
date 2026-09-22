"""Domain exception hierarchy.

All errors raised by business rules and use cases derive from ``DomainError``
so the presentation layer can map them to HTTP responses consistently.
"""


class DomainError(Exception):
    """Base class for every error raised by the domain / application logic."""

    def __init__(self, message: str = "domain error") -> None:
        self.message = message
        super().__init__(message)


# --------------------------------------------------------------------------- #
# Validation errors (400)
# --------------------------------------------------------------------------- #
class EntityValidationError(DomainError):
    """Base class for invalid entity data."""


class UserValidationError(EntityValidationError):
    pass


class InvalidEmailError(UserValidationError):
    pass


class WeakPasswordError(UserValidationError):
    pass


class EventValidationError(EntityValidationError):
    pass


class EventNameLengthError(EventValidationError):
    pass


class EventCodeFormatError(EventValidationError):
    pass


class EventNotInFutureError(EventValidationError):
    pass


class EventCapacityError(EventValidationError):
    pass


class EventPriceError(EventValidationError):
    pass


class BookingValidationError(EntityValidationError):
    pass


class InvalidTicketQuantityError(BookingValidationError):
    pass


class LogValidationError(EntityValidationError):
    pass


# --------------------------------------------------------------------------- #
# Not found (404)
# --------------------------------------------------------------------------- #
class NotFoundError(DomainError):
    pass


class EventNotFoundError(NotFoundError):
    pass


class UserNotFoundError(NotFoundError):
    pass


class BookingNotFoundError(NotFoundError):
    pass


# --------------------------------------------------------------------------- #
# Conflicts (409)
# --------------------------------------------------------------------------- #
class ConflictError(DomainError):
    pass


class EmailAlreadyExistsError(ConflictError):
    pass


class EventCodeAlreadyExistsError(ConflictError):
    pass


class InsufficientTicketsError(ConflictError):
    pass


class EventAlreadyDeletedError(ConflictError):
    pass


# --------------------------------------------------------------------------- #
# Authentication / authorization
# --------------------------------------------------------------------------- #
class AuthenticationError(DomainError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class AuthorizationError(DomainError):
    pass


class NotAdminError(AuthorizationError):
    pass
