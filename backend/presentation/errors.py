"""Mapping from domain errors to DRF HTTP exceptions.

This is a presentation concern: the HTTP status for each business error.
"""

from rest_framework import exceptions as drf_exceptions

from domain import exceptions as domain_exceptions


class Conflict(drf_exceptions.APIException):
    status_code = 409
    default_detail = "Conflict."
    default_code = "conflict"


class InvalidCredentials(drf_exceptions.APIException):
    """401 that is NOT coerced to 403 by DRF's exception handler."""

    status_code = 401
    default_detail = "invalid email or password"
    default_code = "invalid_credentials"


def to_http_exception(exc: domain_exceptions.DomainError) -> drf_exceptions.APIException:
    """Translate a domain error into the corresponding DRF HTTP exception."""
    if isinstance(exc, domain_exceptions.NotFoundError):
        return drf_exceptions.NotFound(detail=exc.message)

    if isinstance(exc, domain_exceptions.InvalidCredentialsError):
        return InvalidCredentials(detail=exc.message)

    if isinstance(exc, domain_exceptions.NotAdminError):
        return drf_exceptions.PermissionDenied(detail=exc.message)

    if isinstance(exc, domain_exceptions.ConflictError):
        return Conflict(detail=exc.message)

    # Any other validation / entity error -> 400
    return drf_exceptions.ValidationError(detail=exc.message)