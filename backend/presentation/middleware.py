"""Request logging middleware.

Persists one LogEntry per request (info for 2xx/3xx, warning for 4xx, error for
5xx) and emits the matching Python log record. Must never break a request.
"""

import logging

from domain.entities.log_entry import AuditContext, LogEntry, LogType
from domain.utils import utcnow

from infrastructure.repositories.django_log_repository import DjangoLogRepository

logger = logging.getLogger("presentation.middleware")

_log_repository = DjangoLogRepository()

from uuid import uuid4  # noqa: E402


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._log_request(request, response)
        except Exception:  # noqa: BLE001 - logging must not break the request
            logger.exception("failed to log request %s %s", request.method, request.path)
        return response

    def _log_request(self, request, response) -> None:
        if response.status_code >= 500:
            log_type = LogType.ERROR
        elif response.status_code >= 400:
            log_type = LogType.WARNING
        else:
            log_type = LogType.INFO

        user_id = None
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            user_id = getattr(user, "id", None)

        entry = LogEntry(
            id=uuid4(),
            created_at=utcnow(),
            type=log_type,
            name=f"http.{request.method.lower()}.{response.status_code}",
            content=f"{request.method} {request.path} -> {response.status_code}",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT"),
            endpoint=request.path,
            http_method=request.method,
            status_code=str(response.status_code),
            user_id=user_id,
        )
        entry.validate()
        _log_repository.create(entry)